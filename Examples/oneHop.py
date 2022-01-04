import simpy
import random, time


import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator

class oneHop_Constrained_Machine(Constrained_Machine):
    """
    A one hop machine. (Simplified)
    Every Machine has an id and a resposnisble id range.
    Upon recieving a request if the machine is not resposnisble for the id, the machine will send it to the correct machine.
    Each machine has knows every others machine's address.
     """

    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, oneHopTable=[], id=0):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.oneHopTable=oneHopTable
        self.id=id
        if not oneHopTable==[]:
            self.id_range=self.find_id_range(self.id)
        self.name=name

    def set_table(self, oneHopTable):
        self.oneHopTable=oneHopTable
        self.id_range=self.find_id_range(self.id)

    def find_id_range(self, id):
        return self.oneHopTable[id]["idrange"]

    def find_address(self, id):
        return self.oneHopTable[id]["address"]

    def _admission_control(self, request):
        if self.check_id(request)==0:
            return Result(0, "Not resposnisble.")
        super()._admission_control(request)

    def check_id(self, request):
        id=request.content
        if not id in range(*self.find_id_range(self.id)):
            self.forward(request)
            return 0
        else:
            print_yellow("Machine " +str(self.id) +" recieved request that its responsible for.")
            return 1

    def forward(self, request):
        id=request.content
        for machine in self.oneHopTable:
            if id in range(*self.find_id_range(machine)):
                self.send_request(machine, request)
                return
        else:
            raise ValueError("Could not find machine resposnisble for id ", id)

    def send_request(self, dst, request):
        if request.valiant>0:
            orig=dst
            dst=random.randint(0, len(self.oneHopTable)-3)
            dst=[entry for entry in self.oneHopTable if not entry in [self.id, orig]][dst]
            request.valiant-=1
            print_red("Machine "+ str(self.id ) + " is forwarding request for "+ str(orig) +" over random machine "+ str(dst))
        else:
            print_purple("Machine "+ str(self.id) + " is forwarding request to responsible machine " + str(dst))
        dst= self.find_address(dst)
        request.start()
        dst.add_request(request)
class oneHopRequest(Request):
    """
    Normal request, with some extra fields for Onehop.
    """
    def __init__( self, n, item, cli_proc_rate, cli_bw, do_timestamp, source, content, valiant=0):
        super().__init__( n, item, cli_proc_rate, cli_bw, do_timestamp)
        self.toOneHop(source, content, valiant)

    def toOneHop(self, source, content, valiant):
        self.source=source
        self.content=content
        self.valiant=valiant #: if valiant is larger than 0 send to random host prior

class oneHopSource(Source):
    """
    Normal source, that sends requests to random oneHop resources.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name=None, maxID=100, valiant=0):
        super().__init__(context, init_n, intensity, weights)
        self.name=name
        self.maxID=maxID
        self.valiant=valiant


    def send_requests(self, dst):
        while True:
            new_request, delta_t = self.generate_request()
            new_request.__class__ = oneHopRequest
            new_request.toOneHop(source=self.name, content=self.fill_content(), valiant=self.valiant)
            yield self.env.timeout(delta_t)
            self.send_request(dst, new_request)

    def fill_content(self):
        return random.randint(0, self.maxID)

def make_OneHop_system(env, ctx, maxID, num_machines, num_sources, verbose, valiant=0):
    oneHopTable=gen_oneHopTable(maxID, num_machines)
    # Create request processing machines
    machines = []
    print("Initialize machines...")
    if num_machines-2<valiant and valiant>0:
        raise ValueError('Not enough machines, ', num_machines, ' for ', valiant, ' valiant hops.')
    for i in range(num_machines):
        s = oneHop_Constrained_Machine(name=f"MACHINE_{i}", context = ctx, bandwidth = 10, space_capacity=10, id=i)
        oneHopTable[i]["address"]=s
        machines.append(s)

    #Update tables entries
    for s in machines:
        s.set_table(oneHopTable)
    # Instantiate Load balancer.
    allocator= Allocator(machines, catalog=ctx.catalog, verbose = verbose)
    load_balancer = RouterLeastCongested(context = ctx, machines=machines, name= "MAIN_ROUTER", \
                                        alloc_map = allocator.allocation_map)

    # Generate oneHopSources
    sources=[]
    for source in range(num_sources):
        src = oneHopSource(context = ctx, intensity = 10, name=source, maxID=maxID, valiant=valiant)
        # instruct the source to send its requests to the load balancer
        env.process(src.send_requests(load_balancer))
        sources.append(src)

    return machines, allocator, load_balancer, sources


def gen_oneHopTable(maxID, num_machines):
    oneHopTable={}
    id_range_len= int(maxID/num_machines)
    last_id=0
    for i in range(num_machines):
        if i==num_machines-1:
            oneHopTable[i]={"idrange": [last_id, maxID+1], "address": []}
        else:
            oneHopTable[i]={"idrange":[last_id, last_id+id_range_len], "address": []}
        last_id+=id_range_len
    return oneHopTable

def  oneHop(valiant=0):

    # Simulation parameters
    num_machines = 10
    catalog_size = 10
    verbose = True
    simulated_time = 100
    num_sources=1
    maxID=100


    # Create a common context
    env = simpy.Environment()
    print("Initialize catalog...")
    catalog = build_catalog(catalog_size)
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    #Generate oneHop system
    machines, allocator, load_balancer, sources=make_OneHop_system(env, ctx, maxID, num_machines, num_sources, verbose=verbose, valiant=valiant)

    # Controller
    Controller(ctx, allocator, load_balancer, verbose = verbose)

    # Let's go!
    print("Run sim...")
    start = time.time()
    env.run(until=simulated_time)
    print("Simulation finished!\n")

    # Print stats
    print("data: ", monitor.data)
    if verbose:
        print("data by name: ", monitor.data_by_name)
    elapsed_time = time.time() - start
    total_requests=sum([src.n for src in sources])
    print("elapsed real time:", elapsed_time, " simulated ", total_requests, " requests. ( ", total_requests/elapsed_time,"reqs/s)")
    print()



if __name__ == "__main__":
    if len(sys.argv)>1:
        if  (not "v" in sys.argv[1]) or (not "=" in sys.argv[1]):
            raise ValueError("Not a valid parameter. Please use v=<valiant hops> to use valiant routing.")
        else:
            valiant=int(sys.argv[1].split("=")[1])
    else:
        valiant=0
    oneHop(valiant)
