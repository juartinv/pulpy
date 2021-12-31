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
        self.id_range=self.find_id_range(self.id)
        self.name=name

    def find_id_range(self, id):
        return self.oneHopTable[id]

    def _admission_control(self, request):
        if self.check_id(request.content)==0:
            return Result(0, "Not resposnisble.")
        super()._admission_control(request)

    def check_id(self, id):
        if not id in range(*self.find_id_range(self.id)):
            self.forward(id)
            return 0
        else:
            print_yellow("Machine " +str(self.id) +" recieved request that its responsible for.")
            return 1

    def forward(self, id):
        for machine in self.oneHopTable:
            if id in range(*self.oneHopTable[machine]):
                print_purple("Forwarding request to responsible machine " + str(machine))
                #TODO send to correct machine
                return
        else:
            raise ValueError("Could not find machine resposnisble for id ", id)


class oneHopSource(Source):
    """
    Normal source, that sends requests to random oneHop resources.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name=None, maxID=100):
        super().__init__(context, init_n, intensity, weights)
        self.name=name
        self.maxID=maxID
    def send_requests(self, dst):
        while True:
            new_request, delta_t = self.generate_request()
            yield self.env.timeout(delta_t)
            new_request.source=self.name
            new_request.content=self.fill_content()
            self.send_request(dst, new_request)
    def fill_content(self):
        return random.randint(0, self.maxID)

def make_OneHop_system(env, ctx, maxID, num_machines, num_sources, verbose):
    oneHopTable=gen_oneHopTable(maxID, num_machines)
    # Create request processing machines
    machines = []
    print("Initialize machines...")
    for i in range(num_machines):
        s = oneHop_Constrained_Machine(name=f"MACHINE_{i}", context = ctx, bandwidth = 10, space_capacity=10, id=i, oneHopTable=oneHopTable)
        machines.append(s)

    # Instantiate Load balancer.
    allocator= Allocator(machines, catalog=ctx.catalog, verbose = verbose)
    load_balancer = RouterLeastCongested(context = ctx, machines=machines, name= "MAIN_ROUTER", \
                                        alloc_map = allocator.allocation_map)

    # Generate oneHopSources
    sources=[]
    for source in range(num_sources):
        src = oneHopSource(context = ctx, intensity = 10, name=source, maxID=maxID)
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
            oneHopTable[i]=[last_id, maxID+1]
        else:
            oneHopTable[i]=[last_id, last_id+id_range_len]
        last_id+=id_range_len
    return oneHopTable

def  oneHop():

    # Simulation parameters
    num_machines = 5
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
    machines, allocator, load_balancer, sources=make_OneHop_system(env, ctx, maxID, num_machines, num_sources, verbose=verbose)

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
    oneHop()
