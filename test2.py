from typing import List
import simpy
from pulpy.interfaces import DefaultContextUser
from pulpy.machines import Machine
from pulpy.system import Context, Monitor, ProbabilityMap, RequestSource, build_catalog, Catalog


# *** SET UP THE CONTEXT ***

# create the usual simpy env
env = simpy.Environment()

# generate a Catalog of Items to query 
catalog : Catalog = build_catalog(10)

# create a monitor for logging purposes
monitor : Monitor = Monitor(env)

# put them together
context = Context(env,monitor,catalog)
DefaultContextUser.set_default_context(context)


# *** CREATE THE ACTUATORS OF THE SCENARIO ***

# create clients
clients : List[RequestSource] = [ RequestSource(prob_map=ProbabilityMap(catalog=catalog,autogenerate_weights=True)) ] * 20

# create a server
server : Machine = Machine('SERVER',context=context)

# *** TELL THE ACTUATORS WHAT TO DO
for c in clients:
    env.process(c.send_requests(server))

# *** START THE SIMULATION ***
env.run(1000)