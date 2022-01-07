import simpy
import random, time


import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator

class FrontendServer(Constrained_Machine):
    """

    """
    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, oneHopTable=[], id=0, backend_servers=None):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.backend_servers=backend_servers
        self.processing={} #{request.name: {requst: x, sent: [], reponses; []}}, .....}
        self.n=0

        #Below are only necesary if you are graphing the system
        self.graphing=False
        self.g=None
        self.frontend_servers=[]
        self.backend_servers=[]
        self.load_balancer=None
        self.sources=None
        self.pos=None


    def _admission_control(self, request):
        super()._admission_control(request)
        if request.__class__==BackendRequest:
            print_yellow("recieved "+str(request.name)+ " response from "+ str(request.source))
            self.processing[request.name]["responses"].append(request.source)
            self.check_backend_response_states(request.name)
        else:
            request.finish_callback = self.call_backend(request)
        self.update_graph(request)

    def check_backend_response_states(self, request_name):
        if len(self.processing[request_name]["responses"])>=len(self.backend_servers):
            print_purple(str(self.name)+ " recieved all necesary responses for "+ str(request_name))
            self.return_to(self.processing[request_name]["request"])
            del self.processing[request_name]
        return

    def request_item(self, item, request_name, backend):
        new_request=BackendRequest(env=self.env, n=self.n, item=item, source=self.name, name=request_name)
        self.update_graph(new_request, dst=backend.name)
        self.n+=1
        new_request.start()
        print_cyan(str(self.name)+ " sent to backend  "+str(backend.name)+ " "+ str(request_name))
        self.processing[request_name]["sent"].append(backend.name)
        backend.add_request(new_request)



    def call_backend(self, request):
        print_purple (str(self.name)+ " callling backend for  " +str(request.name))
        self.processing[request.name]={"request": request, "sent":[], "responses":[]}
        for backend in self.backend_servers:
            item= random.choices(backend.memory, k=1)[0]
            self.request_item(item, request.name, backend)

    def return_to(self, request, dst=None):
        #TODO should I return to the source?
        print_red(str(self.name)+ " returns "+ str(request.name))
        return
    def set_graphing(self, frontend_servers, backend_servers, load_balancer, g, pos, sources):
        self.graphing=graphing
        self.frontend_servers=frontend_servers
        self.backend_servers=backend_servers
        self.load_balancer=load_balancer
        self.g=g
        self.sources=sources
        self.pos=pos
    def update_graph(self, request, dst=None):

        if self.graphing:
            colors=["grey"]*len(self.g.edges)
            if not request.__class__== BackendRequest:
                for l, link in enumerate(self.g.edges):
                    if self.name in link and self.load_balancer.name in link:
                        colors[l]="yellow"
            elif (request.source==self.name):
                for l, link in enumerate(self.g.edges):
                    if self.name in link and dst in link:
                        colors[l]="lime"
            else:
                for l, link in enumerate(self.g.edges):
                    if self.name in link and request.source in link:
                        colors[l]="yellow"
            update_graph(self.frontend_servers, self.backend_servers, self.sources, self.load_balancer, self.pos, self.g, colors=colors, title=str(self.env.now))


class BackendServer(Constrained_Machine):
    """

    """
    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, oneHopTable=[], id=0, frontend_servers=None):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.update_frontend_server_list(frontend_servers)
        self.n=0

    def update_frontend_server_list(self, frontend_servers):
        if frontend_servers:
            self.frontend_servers={frontend.name: frontend for frontend in frontend_servers}

    def _admission_control(self, request):
        super()._admission_control(request)
        if not request.__class__==BackendRequest:
            Result(0, "Not resposnisble.")
        request.finish_callback=(self.return_to(request))

    def request_item(self, item, request_name, backend):
        new_request=BackendRequest(self.env, self.n,item)
        self.n+=1
        new_request.start()
        backend.add_request(new_request)
        self.processing[request.name]["sent"].append(backend.name)

    def return_to(self, request, dst=None):
        if dst==None:
            dst= self.frontend_servers[request.source]
        self.n+=1
        request.source=self.name
        dst.add_request(request)
        return

class BackendRequest(Request):
    """
    Normal request, with a request for content.
    """
    def __init__( self,env, n=0, item=None, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, source=None, name=None):
        super().__init__(env, n, item, cli_proc_rate , cli_bw , do_timestamp )
        self.toBackend(source, name)


    def toBackend(self, source, name):
        self.source=source
        self.name=name

class GraphSource(Source):
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name="Source"):
        super().__init__(context, init_n = 0, intensity = 10, weights = None )
        self.name =name

        self.g=None
        self.frontend_servers=[]
        self.backend_servers=[]
        self.load_balancer=None
        self.sources=None
        self.pos=None
    def set_graphing(self, frontend_servers, backend_servers, load_balancer, g, pos, sources):
        self.graphing=graphing
        self.frontend_servers=frontend_servers
        self.backend_servers=backend_servers
        self.load_balancer=load_balancer
        self.g=g
        self.sources=sources
        self.pos=pos
    def generate_request(self):
        result=super().generate_request()
        #self.update_graph(result[0])
        return result
    def update_graph(self, request):

        colors=["blue"]*len(self.g.edges)
        update_graph(self.frontend_servers, self.backend_servers, self.sources, self.load_balancer, self.pos, self.g, colors=colors)


def  webSearch(graphing):
    # Simulation parameters
    num_backend_servers = 10
    num_frontend_servers =10
    backend_catalog_size = 100
    frontend_catalog_size = 100
    verbose = True
    simulated_time = 100
    num_sources=10

    # Create a common context
    env = simpy.Environment()

    print("Initialize catalog...")
    backend_catalog = build_catalog(backend_catalog_size)
    frontend_catalog = build_catalog(frontend_catalog_size)

    monitor = Monitor(env) # keeps metrics
    frontend_ctx = Context( env, monitor, frontend_catalog)
    backend_ctx = Context( env, monitor, backend_catalog)

    # Create request processing machines
    backend_servers = []
    frontend_servers=[]
    print("Initialize backend Servers...")

    for i in range(num_backend_servers):
        s = BackendServer(name=f"Backend_{i}", context = backend_ctx, bandwidth = 10, space_capacity=10)
        backend_servers.append(s)

    print("Initialize frontend Servers...")

    for i in range(num_frontend_servers):
        s = FrontendServer(name=f"Frontend_{i}", context = frontend_ctx, bandwidth = 10, space_capacity=10)
        frontend_servers.append(s)

    for f in frontend_servers:
        f.backend_servers=backend_servers

    for b in backend_servers:
        b.update_frontend_server_list(frontend_servers)

    print("Allocate backend content...")
    backend_allocator= Allocator(backend_servers, catalog=backend_catalog, verbose = verbose)

    print("Allocate frontend content...")
    frontend_allocator= Allocator(frontend_servers, catalog=frontend_catalog, verbose = verbose)

    load_balancer = RouterLeastCongested(context = frontend_ctx, machines=frontend_servers, name= "MAIN_ROUTER", \
                                        alloc_map = frontend_allocator.allocation_map)

    dummy_router= RouterLeastCongested(context = backend_ctx, machines=backend_servers, name= "router", \
                                        alloc_map = backend_allocator.allocation_map)  #TODO, how to get around this unesecary router
    print("Initialize sources..")
    sources=[]
    for s in range(num_sources):
        src = GraphSource(context = frontend_ctx, intensity = 10, name="Source_"+str(s))
        env.process(src.send_requests(load_balancer))
        sources.append(src)

    Controller(frontend_ctx, frontend_allocator, load_balancer, verbose = verbose)
    Controller(backend_ctx, backend_allocator, dummy_router, verbose = verbose)
    # Let's go!
    if graphing:
        graph(frontend_servers, backend_servers, sources, load_balancer)

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

def graph(frontend_servers, backend_servers, sources, load_balancer, colors=[]):
            frontend_server_horizontal_positon= 4
            source_horizontal_positon=2
            load_balancer_horizontal_positon=3
            backend_server_horizontal_positon=5
            vertical_size_scalar=4
            pos={}
            g=nx.Graph()
            color_choice=["r", "b", "g"]
            for f, frontend in enumerate(frontend_servers):
                g.add_edge(frontend.name, load_balancer.name)
                pos[frontend.name]=(frontend_server_horizontal_positon, f*vertical_size_scalar)

            pos[ load_balancer.name]=(load_balancer_horizontal_positon, int(f/2)*vertical_size_scalar)
            for s, source in enumerate(sources):
                g.add_edge(source.name, load_balancer.name)
                pos[source.name]=(source_horizontal_positon, s*vertical_size_scalar)

            for b, backend in enumerate(backend_servers):
                for f, frontend in enumerate(frontend_servers):
                    g.add_edge(frontend.name, backend.name)
                pos[backend.name]=(backend_server_horizontal_positon, b*vertical_size_scalar)

            for frontend in frontend_servers:
                frontend.set_graphing(frontend_servers, backend_servers, load_balancer, g, pos, sources)
            for source in sources:
                source.set_graphing(frontend_servers, backend_servers, load_balancer, g, pos, sources)

            update_graph(frontend_servers, backend_servers, sources, load_balancer, pos, g, colors)

def update_graph(frontend_servers, backend_servers, sources, load_balancer, pos, g, colors=[], title=" "):
    plt.title("Time "+ title)
    nx.draw_networkx_nodes(g, pos, nodelist=[n.name for n in frontend_servers], node_color="green")
    nx.draw_networkx_nodes(g, pos, nodelist=[n.name for n in backend_servers], node_color="blue")
    nx.draw_networkx_nodes(g, pos, nodelist=[s.name for s in sources], node_color="red")
    nx.draw_networkx_nodes(g, pos, nodelist=[load_balancer.name], node_color="yellow")
    if colors==[]:
        colors=["grey"]* len(g.edges)
    nx.draw_networkx_edges(g, pos, edgelist=g.edges, edge_color=colors, width=1 )
    """for c, connection in enumerate(network.connections):
        nx.draw_networkx_edges(g, pos, edgelist=[connection.nodes], edge_color="black", width=2 )"""

    nx.draw_networkx_labels(g, pos, font_size=8)
    plt.axis('off')
    plt.tight_layout()
    plt.draw()
    plt.pause(.000001)


if __name__ == "__main__":
    graphing=False
    if len(sys.argv)>1:
        if  (not "-g" in sys.argv):
            raise ValueError("Not a valid parameter. Please use -g to visualize system.")
        if ("-g" in sys.argv):
            import networkx as nx
            import matplotlib.pyplot as plt
            graphing=True

    webSearch(graphing)
