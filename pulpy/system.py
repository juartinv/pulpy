from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple
from simpy import Environment
import numpy as np
from collections import OrderedDict
from pulpy.fun import *
from pulpy.interfaces import *
from pulpy.machines import CoreMachine
from pulpy.alloc import AllocationMap


#utils
def build_job_catalog(catalog_size, max_item_work = 10):
    """
    Initializes a catalog of potential jobs.
    Job catalog is the size of catalog_size
    Job names = {0, ...., catalog_size}
    Job work random int between (1, max_item_work)
    """
    c = Catalog()
    c.items = [Job(f"item_{name}", random.randint(1, max_item_work)) for name in range(catalog_size) ]
    return c

def build_catalog(catalog_size, max_item_work = 10, max_item_size = 10):
    """
    Initializes a catalog of potential resource items.
    Catalog is the size of catalog_size.
    names = {0, ...., catalog_size}
    Item work random int between (1, max_item_work)
    Item size random int between (1, max_item_size)
    """
    c = Catalog()
    c.items = [Item(f"item_{name}", random.randint(1, max_item_work), random.randint(1, max_item_work)) for name in range(catalog_size) ]
    return c

class Context(object):
    """
    Generic container for common instances required by other objects.
    Including:
        SimPy Environment (env)
        Monitor
        Catalog (Jobs of Resource Items)
    """
    def __init__(self, env: Environment, monitor: Monitor, catalog: Catalog):
        self.env = env
        self.monitor = monitor
        self.catalog = catalog

class CoreRequestSource(object):
    """
    Parent class of all Request Sources.
    generates and sends requests.
    """
    def __init__(self, init_n: int = 0):
        self.n = init_n   # request counter

    def send_request(self, dst: CoreMachine, request: Request):
        request.start()
        dst.add_request(request)

    def generate_request(self, item: Item) -> Request:
        # simple impementation
        self.n += 1
        new_req = Request(self.env, self.n, item)
        return new_req

class RequestSource(CoreRequestSource):
    """
    Sends requests according to given popularity map.
    """
    def __init__(self,  init_n: int = 0, prob_map: Optional[ProbabilityMap] = None):
        super().__init__(init_n)
        self.prob_map = None
        if prob_map:
            self.update_probability_map(prob_map)
        self.next_batch = []

    def update_probability_map(self, prob_map: ProbabilityMap):
        self.prob_map = prob_map
        self.catalog = prob_map.catalog
        self.catalog_weights = prob_map.get_all_probabilities(as_list=True)

    def generate_request(self) -> Tuple[Item,float]:
        """
        This function is used to generate tuples (request, firing_time).
        """
        # just rewrite it to your convenience. Defaults to Poisson events
        # chosen accordingly to a probability map.
        if not self.prob_map:
            raise Exception("No probability map found, can't generate requests.")

        if not self.next_batch:
            batch_size = 1000
            r = random.choices(self.catalog.get(), self.catalog_weights, k=batch_size)
            dt = [random.expovariate(self.prob_map.intensity) for _ in range(batch_size)]
            # FIXME!!! what if theres no prob_map ?
            self.next_batch = list(zip(r,dt))

        item, delta_t  = self.next_batch.pop()
        new_req = super().generate_request(item)
        return (new_req, delta_t)

    def send_requests(self, dst: CoreMachine):
        while True:
            new_request, delta_t = self.generate_request()
            yield self.env.timeout(delta_t)
            self.send_request(dst, new_request)


class Source(ContextUser, RequestSource):
    """
     Creates and emits requests
     """
    def __init__(self, context: Context, init_n: int = 0, intensity: int = 10, weights: Optional[List|Dict|np.ndarray] = None):
        ContextUser.__init__(self, context)
        RequestSource.__init__(self, init_n = init_n)
        prob_map = ProbabilityMap(self.catalog)
        if not weights:
            prob_map.generate_weights()
        else:
            prob_map.allocate_weights(weights)
        prob_map.intensity = intensity
        self.update_probability_map(prob_map)


class PeriodicSource(ContextUser, CoreRequestSource):
    """
     Creates and emits requests periodicly.
     (Every x time increments request y is made)
     """
    def __init__(self, context: Context, init_n: int = 0, intensity: int = 10, min_interval:int = 3, max_interval:int = 10, latest_start_time: int =5, verbose:bool=False):
        ContextUser.__init__(self, context)
        CoreRequestSource.__init__(self, init_n = init_n)
        assert(min_interval< max_interval)
        self.dst=None
        self.max_interval=max_interval
        self.min_interval=min_interval
        self.latest_start_time=latest_start_time
        self.verbose=verbose

    def send_request(self, dst: CoreMachine, request: Request):
        new_req = self.generate_request(request)
        new_req.start()
        dst.add_request(new_req)

    def send_requests(self, dst: CoreMachine):
        self.dst=dst
        for item in self.catalog.get_iterator():
            self.env.process(PeriodicRequest(item, self, start_time=random.randint(0,self.latest_start_time), interval=random.randint(self.min_interval,self.max_interval)).run())
        yield self.env.timeout(1e6)


class PeriodicRequest():
    """
    Sends the same request every interval time starting at start time.
    """
    def __init__(self, item, source, start_time, interval):
        self.item=item
        self.source=source
        self.start_time=start_time
        self.interval=interval
        if self.source.verbose:
            print ("Starting periodic request for: ", self.item.name, " with start time ", self.start_time, " and interval of: ", self.interval)
    def run(self):
        if self.source.dst==None:
            if self.source.verbose:
                print_red("No destination to send request to.")
            return

        yield self.source.env.timeout(self.start_time)
        while True:
            self.source.send_request( self.source.dst, self.item)
            if self.source.verbose:
                print ("Sent request at time ", self.source.env.now, " for item ", self.item.name)
            yield self.source.env.timeout(self.interval)
        return

class Monitor(Observer, object):
    """
    Observer Object used to monitor simulation.
    """
    def __init__(self, env: Environment):
        self.env=env
        self.start_time=self.env.now

        self.errors=[]

        self.data = dict() # counters and data
        self.data_by_name = dict()
        self.ts = dict()   # time series

        self.last_print = 0
        self.print_every = 50

        self.max_log_length = 100
        self.head = 0

    def update(self, name, report:Report):
        assert isinstance(report,Report)
        assert isinstance(report.value, dict)
        for k,v in report.value.items():
            if name not in self.data_by_name.keys():
                self.data_by_name[name] = dict()
            if k not in self.data_by_name[name].keys():
                self.data_by_name[name][k] = 0
            self.data_by_name[name][k] += v
            if k not in self.data.keys():
                self.data[k] = 0
            self.data[k] += v
        if self.env.now - self.last_print > self.print_every:
            self.last_print       = self.env.now
            print("    ----------: ", self.data, "running time:", self.env.now)

    def updatets(self, report):
        assert isinstance(report,Report)
        assert isinstance(report.value, dict)
        for k,v in report.value.items():
            if k not in self.ts.keys():
                self.ts[k] = []
            self.ts[k].append(v)


class Report(Token):
    __slots__ = ["id", "type","value"]
    def __init__(self, id, value ):
        assert isinstance(value, dict)
        self.value = value
        super().__init__(id, type = "Report")

class Result(Token):
    __slots__ = ["id", "type", "result", "reason"]
    def __init__(self, result, reason = None ):
        assert isinstance(result, int)
        self.result = result
        if result != 0:
            assert reason
            self.reason = reason
        super().__init__(id = None, type = "Result")

    def __bool__(self):
        return self.result == 0

class Item(object):
    """
    Object that can be requested by users.
    """
    __slots__ = ["name", "work", "size","life_cycle"]
    def __init__(self, name, work, size, life_cycle=0):
        self.name = name
        self.work = work
        self.size = size
        self.life_cycle = life_cycle
        # two lifecycles:
        #  0: first exhaust work, then transfer (default).
        #  1: simoultaneously consume work and transfer.

class Content(Item):
    """
     Content object (file) that can be requested by users.
     """
    def __init__(self, name, size):
        work = 0
        super().__init__(name, work, size)

class Job(Item):
    """
    Task to be executed, requested by users.
    """
    def __init__(self, name, work):
        size = 0
        super().__init__(name, work, size)

class Catalog(object):
    """
     Catalog of all possible items.
     """
    def __init__(self):
        self.items = list()

    def get_size(self):
        return len(self.items)

    def put(self, item):
        assert isinstance(item, Item)
        if item in self.items:
            return "Item already in catalog"
        self.items.append(item)

    def drop(self, item):
        if item not in self.items:
            return "Item not in catalog"
        self.items.remove(item)

    def get(self):
        return self.items

    def get_iterator(self):
        for i in self.items:
            yield i

    def get_map(self):
        for i in self.items:
            yield (i.name, i.work)

    def item_obj_from_name(self, item_name):

        for i in self.get():
            if i.name==item_name:
                return i
        else:
            raise ValueError ("Item with name: ", item_name, " not in catalog.")

class Request(object):
    """
    Request Object.
    Can be a request for Work or Space.
    """
    _NOT_INIT = 0
    _STARTED = 1
    _FINISHED = 2
    _PAUSED = 3

    def __init__(self,env, n, item, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False):
        assert isinstance(item, Item)
        self.env = env
        self.item = item  #an Item object

        self.state = Request._NOT_INIT
        self.remaining_work = item.work   # amount of work required to finish the requested task.
        self.cli_proc_rate = cli_proc_rate  # Client's processing rate or bandwith

        self.remaining_size = item.size   # amount of pending space transfer required to finish the requested task.
        self.cli_bw = cli_bw  # Client's processing rate or bandwith

        self.name = item.name
        self.n = n
        self.start_time = None
        self.do_timestamp = do_timestamp
        self.finish_callback = None    #update to do an action on request being finished

    def _process(self, target_resource, target_cap, delta_t, quota, wanted = None):
        if not wanted:
            wanted = min(target_cap*delta_t, target_resource)
        margin = quota - wanted
        if margin > 0:
            # We didn't use that much
            target_resource = 0
        else:
            # we used all and could use a little extra
            target_resource -= quota
        return margin, target_resource

    def process(self, resource, delta_t, quota, wanted = None):
        # Resource must be one of "work" or "space"
        if resource == "work":
            margin, self.remaining_work = self._process(self.remaining_work, self.cli_proc_rate, delta_t, quota, wanted)
        elif resource == "space":
            margin, self.remaining_size = self._process(self.remaining_size, self.cli_bw, delta_t, quota, wanted)
        else:
            raise Exception("ProcessingError: Unknown resource.")

        if self.remaining_work <= 0 and self.remaining_size <=0:
            self.finish()
        return margin

    def _estimate_time(self, target_resource, target_cap, cap = None):
        div = target_cap
        if cap:
            div = min(div, cap)
        expected_time =  target_resource / div
        return expected_time

    def estimate_time_to_completition(self, proc_rate_cap = None):
        return self._estimate_time(self.remaining_work , self.cli_proc_rate, proc_rate_cap)

    def estimate_remaining_transfer_time(self, bw_cap = None):
        return self._estimate_time(self.remaining_size , self.cli_bw, bw_cap)

    def start(self):
        if self.state ==  Request._STARTED:
            return
        self.state = Request._STARTED
        if self.do_timestamp:
            self.start_time = self.env.now

    def finish(self):
        if self.state ==  Request._FINISHED:
            return
        self.state = Request._FINISHED
        if self.do_timestamp:
            self.finish_time = self.env.now
        if self.finish_callback:
            self.finish_callback()

    def update_finish_callback(f):
        self.finish_callback = f

    def is_alive(self):
        return self.state != self._FINISHED

    def may_process_size(self):
        if self.item.life_cycle == 1:
            return True
        if self.item.life_cycle == 0 and self.remaining_work <= 0:
            return True
        return False




class ProbabilityMap(object):
    """
     This object augments a catalog by adding popularities.
     """
    def __init__(self, catalog):
        self.catalog = catalog
        self.map = OrderedDict()
        self.intensity = 1
        self.np_popularity = None

    def __iter__(self):
        return self.map.__iter__()

    def generate_weights(self, method = "uniform"):
        if method == "uniform":
            w = [random.random() for _ in range(self.catalog.get_size())]
            w = sorted( [i/sum(w) for i in w  ] )[::-1]
        elif method == "equal":
            w = [1/l for _ in range(self.catalog.get_size())]
        self.allocate_weights(w)

    def allocate_weights(self, weights):
        # Note: weights must be non increasing, non-negative values

        if isinstance(weights, list):
            keys = self.catalog.get()
            wnp = np.array(weights)

        elif isinstance(weights, np.ndarray):
            keys = self.catalog.get()
            wnp = weights

        elif isinstance(weights, dict ):
            lt = sorted(weights.items(), key = lambda v: -v[1])  #list of tuples
            self.map = OrderedDict(lt)   #recall that zip will result in the min length
            keys = self.map.keys()
            wnp = np.array(list(self.map.values()))

        else:
            raise Exception("Inknown popularity format.")

        if len(wnp.shape) != 1:
            raise Exception("Bad probability vector dimensions.")

        if min(wnp) < 0:
            raise Exception("Bad probability vector contains negative value.")

        if (len(wnp)>1): # Incase we only have one item that has already been requested
            if min(np.diff(wnp)) > 0:
                raise Exception("Bad probability vector contains some strictly increasing values.")

        self.intensity = wnp.sum()
        wnp = wnp / self.intensity   # normalize

        self.map = OrderedDict( zip(keys, wnp))   #recall that zip will result in the min length
        self.np_popularity = wnp

    def get_pop(self, item):
        return self.map[item]

    def get_intensity(self):
        return self.intensity

    def get_map(self):
        return self.map

    def get_pop_array(self):
        return self.np_popularity

    def get_all_probabilities(self, as_list=False):
        if as_list:
            return list(self.map.values())
        else:
            return self.map.values()
