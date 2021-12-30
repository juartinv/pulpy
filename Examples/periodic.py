import simpy
import random, time


import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator



def  periodic():

    # Simulation parameters
    num_machines = 50
    catalog_size = 30
    verbose = True
    simulated_time = 100

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
        s = Constrained_Machine(name=f"MACHINE_{i}", context = ctx, bandwidth = 10, space_capacity=10)
        machines.append(s)

    # Instantiate Load balancer.
    allocator= Allocator(machines, catalog=ctx.catalog, verbose = verbose)
    load_balancer = RouterLeastCongested(context = ctx, machines=machines, name= "MAIN_ROUTER", \
                                        alloc_map = allocator.allocation_map)

    # Generate PeriodicSources
    src = PeriodicSource(context = ctx, intensity = 10, verbose=verbose)

    # instruct the source to send its requests to the load balancer
    env.process(src.send_requests(load_balancer))
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
    print("elapsed real time:", elapsed_time, " simulated ", src.n, " requests. ( ", src.n/elapsed_time,"reqs/s)")
    print()



if __name__ == "__main__":
    periodic()
