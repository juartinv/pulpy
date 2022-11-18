from typing import List
import simpy
import random
from pulpy.interfaces import DefaultContextUser
from pulpy.machines import Machine, Router
from pulpy.system import Context, Monitor, ProbabilityMap, RequestSource, build_catalog, Catalog, SimpleRequestSource


# *** SET UP THE CONTEXT ***

# create the usual simpy env
env = simpy.Environment()

# generate a Catalog of Items to query
catalog : Catalog = build_catalog(10)   # I think this is not actually needed

# create a monitor for logging purposes
monitor : Monitor = Monitor(env)

# put them together
context = Context(env,monitor,catalog)
DefaultContextUser.set_default_context(context)

class P4SwitchForDNS(Router):

    def __init__(self, name, context):
        super().__init__(context, [], name)
        self.white_list = set()
        self.black_list = set()
        self.dns_servers = []
        self.expert_servers = []

    def route_request(self, request):
        if request.name in self.white_list:
            m = random.choice(self.dns_servers)
        elif request.name in self.black_list:
            m = random.choice(self.expert_servers)
        else:
            # NOTE: put custom ideas gere
            m = random.choice(self.expert_servers)

        #self.stats[m] += 1
        res = m.add_request(request)

    def instruct_controlplane(self,instruction):
        if instruction["type"]=='INSERT_WHITELIST':
            self.white_list.add(instruction["domainname"])
        elif instruction["type"]=='INSERT_BLACKLIST':
            self.black_list.add(instruction["domainname"])
        elif instruction["type"]=='REMOVE_WHITELIST':
            self.white_list.remove(instruction["domainname"])
        elif instruction["type"]=='REMOVE_BLACKLIST':
            self.black_list.remove(instruction["domainname"])
        else:
            raise NotImplementedError("Instruction type is not implemented.")

# *** CREATE THE ACTUATORS OF THE SCENARIO ***

# create clients
# client = RequestSource(prob_map=ProbabilityMap(catalog=catalog,autogenerate_weights=True))
candidates = ["example1.com", "example2.com", "example3.com", "example4.com","example5.com"]
client = SimpleRequestSource()
client.set_candidates(candidates)


# create a server
dns_server : Machine = Machine('DNS_SERVER',context=context)
expert_server : Machine = Machine('EXP_SERVER',context=context)
p4_switch = P4SwitchForDNS('P4Switch',context=context)
p4_switch.dns_servers = [dns_server]
p4_switch.expert_servers = [expert_server]


# *** TELL THE ACTUATORS WHAT TO DO
env.process(client.send_requests(p4_switch))

# *** START THE SIMULATION ***
env.run(1000)
