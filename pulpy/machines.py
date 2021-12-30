import random
import simpy
from pulpy.system import *
from pulpy.fun import *

class CoreMachine(ContextUser, CoreRequestSource, object):
    """
    Parent class of all machines.
    Machines can be a variety of abstracted distributed entities.
    """
    def __init__(self,context):
        ContextUser.__init__(self, context)
        CoreRequestSource.__init__(self)
        self.working_set = []
        self.last_visit  = 0
        self.next_event = None

        self.action = self.env.process(self.run())

        # space, processing and bandwidth are the main characteristics.
        # although they can be ommited, at least one must be defined.

        self.bandwidth = 0           # Bandwidth requirements
        self.capacity = 0            # RAM or disk space requirements
        self.proc_power = 0          # Processing power

    def send_request(self, dst, request):
        dst.add_request(request)

    def _admission_control(self, request):
        assert isinstance(request, Request)
        return Result(0)

    def add_request(self,request):
        raise NotImplementedError

    def get_concurrency(self):
        return len(self.working_set)

    def update_visit_time(self):
        delta_visit = self.env.now - self.last_visit
        self.last_visit = self.env.now
        return delta_visit

    def process_elapsed_time(self, verbose = False):
        ini_r = self.get_concurrency()
        delta_visit = self.update_visit_time() # time since last visit
        self.working_set = self.process_requests(delta_visit, verbose = verbose)
        if not self.get_concurrency():
            self.next_event = None

    def compute_next_expected_completition_time(self):
        # This is processing specific.
        raise NotImplementedError

    def update_next_event(self):
        if not self.get_concurrency():
            self.next_event = None
            return

        next_expected_completition_time = self.compute_next_expected_completition_time()
        if next_expected_completition_time < 1e-9:
            next_expected_completition_time = 1e-9

        self.next_event = self.env.timeout(next_expected_completition_time)

    def process_requests(self, delta_visit, verbose = False):
        raise NotImplementedError

    def run(self):
        #This process controls time until next service completition.
        while True:
            try:
                if not self.next_event:
                    yield self.env.timeout(1e6)
                    continue

                yield self.next_event
                self.process_elapsed_time(verbose = True)

            except simpy.Interrupt:
                pass

            self.update_next_event()


class Machine(Observable, CoreMachine, object):
    """
     A simple processor sharing server class.
     """
    def __init__(self, name, context, bandwidth = 10000.0, proc_power = 10000):
        CoreMachine.__init__(self, context)
        self.bandwidth = bandwidth        # bandwidth capacity
        self.proc_power = proc_power      # Processing power

        Observable.__init__(self, name)
        self.add_observer(self.monitor)

        # function used for processing disicplines.
        self._process = self.processor_sharing_process
        # self._process = self.fifo_process

    def add_request(self,request):
        admitted = self._admission_control(request)
        if not admitted:
            return admitted  # a Result object

        self.process_elapsed_time()
        self.working_set.append(request)
        self.action.interrupt()   #FIXME??

        t = Result(0)
        trep = Report(None, {"hit": 1})
        self.notify_observer(trep)

        return t

    def processor_sharing_process(self, delta_visit, work_quota = 0, size_quota = 0 ):
        # Processor sharing discipline

        def _distribute_quota(resource, quota, to_update):
            if not quota:
                return
            individual_quota =  quota
            margins = {req:0 for req in to_update}
            while (individual_quota > 0) and to_update:
                # positive margins can be redistributed.
                individual_quota =  quota / len(to_update)
                margins = {req: req.process(resource, delta_visit, individual_quota,
                           wanted = -margins[req]) for req in to_update }
                to_update = [req for req,v in margins.items() if v < 0]
                quota = sum([v for _,v in margins.items() if v > 0])


        if not self.get_concurrency():  # if no active requests return
            return self.working_set

        # Process work
        _distribute_quota("work", work_quota, self.working_set)

        # Now process sizes according to lifecycles!
        to_update = [req for req in self.working_set if req.may_process_size()]
        if len(to_update):
            _distribute_quota("space", size_quota, to_update)

        incomplete = list(filter( lambda x:x.is_alive(), self.working_set))
        return incomplete


    def fifo_process(self, delta_visit, work_quota = 0, size_quota = 0 ):
        # fifo processing
        if not self.get_concurrency():  # if no active requests return
            return self.working_set


        for req in self.working_set:
            work_quota = req.process("work", delta_visit, work_quota)
            if req.may_process_size():
                size_quota = req.process("work", delta_visit, size_quota)
            if work_quota <= 0 and size_quota <= 0:
                break

        # incomplete = list(filter( lambda x:x.remaining_work > 0 or x.remaining_size > 0, self.working_set) )  #FIXME
        incomplete = list(filter( lambda x:x.is_alive(), self.working_set))
        return incomplete

    def process_requests(self, delta_visit, verbose = False):

        incomplete = self.working_set
        if self.get_concurrency():  # if there is at least one active request
            required_processing = min(self.proc_power, sum([req.cli_proc_rate for req in self.working_set]))
            work_quota = delta_visit*required_processing

            required_processing = min(self.bandwidth, sum([req.cli_bw for req in self.working_set]))
            size_quota = delta_visit*required_processing
            incomplete = self._process(delta_visit, work_quota, size_quota)

            t = Result(0)
            self.notify_observer(Report(None, {"work":work_quota, "space": size_quota}))

        return incomplete

    def compute_next_expected_completition_time(self):
        nominal_power = min(self.proc_power, sum([req.cli_proc_rate for req in self.working_set])) / self.get_concurrency()
        expected_completition_times = [req.estimate_time_to_completition(proc_rate_cap = nominal_power) for req in self.working_set]
        next_expected_completition_time = min(expected_completition_times)

        nominal_bw = min(self.bandwidth, sum([req.cli_bw for req in self.working_set])) / self.get_concurrency()
        expected_completition_times = [req.estimate_remaining_transfer_time(bw_cap = nominal_bw) for req in self.working_set]
        next_expected_completition_time_transfer = min(expected_completition_times)

        if not next_expected_completition_time:
            return next_expected_completition_time_transfer
        return min(next_expected_completition_time, next_expected_completition_time_transfer)


class Constrained_Machine(Machine):
    """
    A cpu, space and bandwidth-constrained machine.
    This machine can only accept and process requests to items already known on its Memory.
     Similar to the machine class, they also have finite processing power and bandwidth.
     Finally there is also a hard limit on concurrency (size of the working set),
     which is the usual case in many operative systems.
     """

    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10,):

        super().__init__( name, context, bandwidth)
        self.memory = []
        self.capacity = space_capacity
        self.remaining_capacity = space_capacity
        self.hard_limit_concurrency = hard_limit_concurrency

    def _admission_control(self, request):
        super()._admission_control(request)

        if self.get_concurrency() >= self.hard_limit_concurrency:
            t = Result(1, reason = "Connection pool depleted")   #Connection pool depleted.
            trep = Report(None, {"depleted_pool": 1})
            self.notify_observer(trep)
            return t

        if not (request.item in self.memory):
            t = Result(2, reason = "Item not in memory")   #Item not in memory
            trep = Report(None, {"item_not_in_memory": 1})
            self.notify_observer(trep)
            return t

        return Result(0)

    def get_memory(self):
        return self.memory

    def fetch(self, item):   # what should we return?
        if item in self.memory:
            return Result(3, reason = "Item already in Memory")

        if self.remaining_capacity >= item.work:
            self.memory.append(item)
            self.remaining_capacity -= item.work
            return Result(0)
        else:
            raise Exception("FetchError: Not enough space to store item.")
            # return Result(4, reason = "FetchError: Not enough space to store item.")

    def evict(self, item):   # what should we return?
        if item not in self.memory:
            # raise Exception("EvictionError: Item not in memory")
            t = Result(2, reason = "Item not in memory")   #Item not in memory
            trep = Report(None, {"item_not_in_memory": 1})
            self.notify_observer(trep)
            return t
        self.memory.remove(item)
        self.remaining_capacity += item.work
        return Result(0)


class Router(Observable, object):
    """
    The balancer: receives requests and distributes them.
    """

    def __init__(self, context, machines, name):
        super().__init__(name)
        self.context = context
        self.env = context.env
        self.monitor=context.monitor
        self.add_observer(self.monitor)
        self.name = name
        self.machines = machines

        #stats
        self.stats = {d:0 for d in machines}

    def add_request(self, request):
        self.route_request(request)

    def route_request(self, request):
        m = random.choices(self.machines)[0]
#         print ("Sending request " , request.item.name, " to cache ", cache.name, " with queue length", cache.get_concurrency())
        self.stats[m] += 1
        res = m.add_request(request)

    def push_alloc_map(self, alloc_map):
        self.alloc_map = alloc_map


class RouterLeastCongested(Router):
    """
     The balancer: receives requests and distributes them. This one is aware of the object allocation in caches.
     """
    def __init__(self, context, machines, name, alloc_map):
        # Not the bottleneck!
        self.alloc_map = alloc_map
        super().__init__(context, machines, name)

    def route_request(self, request):
        a = self.alloc_map.alloc_o
        candidate_targets = []
        if request.item in a.keys():
            candidate_targets = self.alloc_map.alloc_o[request.item]

        if not candidate_targets:
            request.finish()  # We don't know what to do with this.
            t = Result(10, "Dropped because we don't know what to do with this.")
            trep = Report(None, {"dropped": 1})
            self.notify_observer(trep)
            return

        concurrency = [m.get_concurrency() for m in candidate_targets]
        machine = [m for m in candidate_targets if m.get_concurrency() == min(concurrency)][0]
        res = machine.add_request(request)
        self.stats[machine] += 1
