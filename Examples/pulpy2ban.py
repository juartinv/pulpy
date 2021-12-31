import simpy
import random, time


import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator

class pulpy2ban_Constrained_Machine(Constrained_Machine):
    """
     blocks all requests from a source that was deemed to be "malicous"
     for x amount of time where x increase exponentially everytime a "malicous" request occurs.
     """

    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.pulpy2ban_logs={}
        self.initial_ban_time=2
        self.verbose= verbose

    def _admission_control(self, request):
        super()._admission_control(request)
        if self.pulpy2ban(request):
            return Result(1, "banned" )
        else:
            print_cyan("Request from source " + str(request.source) + " passed pulpy2ban's checks.")

    def pulpy2ban(self, request):
        if request.source in self.pulpy2ban_logs:
            ban_time= self.initial_ban_time ** self.pulpy2ban_logs[request.source][0]
            banned_till= self.pulpy2ban_logs[request.source][1]+ ban_time
            if self.env.now< banned_till:
                if self.verbose:
                    print_red("Source " + str(request.source)+ " is banned till "+ str(banned_till))
                return 1

        if self.is_malicous(request):
            self.ban(request)
            return 1
        else:
            return 0

    def is_malicous(self, request):
        if "malicous" in request.content:
            if self.verbose:
                print_red( "Source " + str(request.source)+ " has been identified as malicious")
            return 1
        else:
            return 0

    def ban(self, request):
        if self.verbose:
            print_red("Banning " + str(request.source))
        if not request.name in self.pulpy2ban_logs:
            self.pulpy2ban_logs[request.source]=[0, self.env.now]
        else:
            self.pulpy2ban_logs[request.source][0]+=1
            self.pulpy2ban_logs[request.source][1]=self.env.now

class MalicousSource(Source):
    """
    Normal source, that sometimes sends "Malicious" requests.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name=None):
        super().__init__(context, init_n, intensity, weights)
        self.name=name
        self.malicious_frequency=20 # in percent

    def send_requests(self, dst):
        while True:
            new_request, delta_t = self.generate_request()
            yield self.env.timeout(delta_t)
            new_request.source=self.name
            new_request.content=self.fill_content()
            self.send_request(dst, new_request)

    def fill_content(self):
        if self.malicious_frequency>= random.randint(0,100):
            return "malicous request"
        else:
            return "normal request"


def  pulpy2ban():

    # Simulation parameters
    num_machines = 50
    catalog_size = 30
    verbose = True
    simulated_time = 100
    sources=10

    # Create a common context
    env = simpy.Environment()
    print("Initialize catalog...")
    catalog = build_catalog(catalog_size)
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    # Create request processing machines
    machines = []
    print("Initialize machines...")
    for i in range(num_machines):
        s = pulpy2ban_Constrained_Machine(name=f"MACHINE_{i}", context = ctx, bandwidth = 10, space_capacity=10)
        machines.append(s)

    # Instantiate Load balancer.
    allocator= Allocator(machines, catalog=ctx.catalog, verbose = verbose)
    load_balancer = RouterLeastCongested(context = ctx, machines=machines, name= "MAIN_ROUTER", \
                                        alloc_map = allocator.allocation_map)

    # Generate Potentially Malicious Sources
    sources=[]
    for source in range(sources):
        src = MalicousSource(context = ctx, intensity = 10, name=source)
        # instruct the source to send its requests to the load balancer
        env.process(src.send_requests(load_balancer))
        sources.append(src)

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
    pulpy2ban()
