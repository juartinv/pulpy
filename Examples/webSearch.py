import simpy
import random, time
import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator
grey= (.33,.33,.31)


class FrontendServer(Constrained_Machine):
    """
    Server recives a request proccesses that request, then asks every backend server for a resource.
    """
    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, oneHopTable=[], id=0, backend_servers=None, sources=[]):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.backend_servers=backend_servers
        self.processing={} #{request.name: {requst: x, sent: [], reponses; []}}, .....}
        self.n=0
        self.update_source_list(sources)
        self.complete_requests=0
        #Below are only necesary if you are graphing the system
        self.g=None
        self.colors=None

    def update_source_list(self, sources):
        if sources:
            self.sources={source.name: source for source in sources}

    def _admission_control(self, request):
        super()._admission_control(request)
        if request.__class__==BackendRequest: # Check to see if this is a response from the backend
            if self.verbose:
                print_yellow("recieved "+str(request.name)+ " response from "+ str(request.source))
            self.processing[request.name]["responses"].append(request.source)
            self.check_backend_response_states(request.name)
        else: #Request from source
            request.finish_callback = self.call_backend(request) #Set to call backend once proccesed
        self.update_graph(request)

    def check_backend_response_states(self, request_name):
        """
        See if server has recieved responses from all backend_servers.
        """
        if len(self.processing[request_name]["responses"])>=len(self.backend_servers):
            if self.verbose:
                print_purple(str(self.name)+ " recieved all necesary responses for "+ str(request_name))
            self.return_to(self.processing[request_name]["request"])
            del self.processing[request_name]
        return

    def request_item(self, item, request_name, backend):
        """
        Request a random cached item from a single backend server.
        """
        new_request=BackendRequest(env=self.env, n=self.n, item=item, source=self.name, name=request_name)
        self.update_graph(new_request, dst=backend.name)
        self.n+=1
        new_request.start()
        if self.verbose:
            print_cyan(str(self.name)+ " sent to backend  "+str(backend.name)+ " "+ str(request_name))
        self.processing[request_name]["sent"].append(backend.name)
        backend.add_request(new_request)

    def call_backend(self, request):
        """
        Request a random cached item from all backend servers.
        """
        if self.verbose:
            print_purple (str(self.name)+ " callling backend for  " +str(request.name))
        self.processing[request.name]={"request": request, "sent":[], "responses":[]}
        for backend in self.backend_servers:
            if len(backend.memory)>=1:
                item= random.choices(backend.memory, k=1)[0]
                self.request_item(item, request.name, backend)

    def return_to(self, request, dst=None):
        """
        Return finihsed request to source
        """
        if self.verbose:
            print_red(str(self.name)+ " returns "+ str(request.name))
        self.sources[request.source].add_request(Request(env=self.env, n=self.n, item=request.item))
        if self.colors:
            self.colors.set_color(A=self.name, B=request.source,  color=grey)
            self.colors.set_color(A=self.name, B=request.source,  color="green")
        self.complete_requests+=1
        return

    def set_graphing(self, colors, load_balancer):
        """
        Tell server to update values for graph.
        """
        self.colors=colors
        self.load_balancer=load_balancer

    def update_graph(self, request, dst=None):
        """
        Update graph colors depending on where the request came from.
        """
        if self.colors:
            if not request.__class__== BackendRequest:
                self.colors.set_color(A=self.name, B=self.load_balancer.name, color="yellow")
            elif (not dst==None and request.source==self.name):
                self.colors.set_color(A=self.name, B=dst,  color="green")
            else:
                self.colors.set_color(A=self.name, B=request.source,  color="blue")

class BackendServer(Constrained_Machine):
    """
    Waits for requests from the frontend_servers.
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
        request.finish_callback=(self.return_to(request)) #Upon complition of request return to frontend_server

    def return_to(self, request, dst=None):
        """
        Return to frontend_server
        """
        if dst==None:
            dst= self.frontend_servers[request.source]
        self.n+=1
        request.source=self.name
        dst.add_request(request)
        return

class BackendRequest(Request):
    """
    Normal request, with a request to a backend_server for content.
    """
    def __init__( self,env, n=0, item=None, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, source=None, name=None):
        super().__init__(env, n, item, cli_proc_rate , cli_bw , do_timestamp )
        self.toBackend(source, name)

    def toBackend(self, source, name):
        self.source=source
        self.name=name
class FrontendRequest(Request):
    """
    a request to a frontend_server.
    """
    def __init__( self,env, n=0, item=None, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, source=None, name=None):
        super().__init__(env, n, item, cli_proc_rate , cli_bw , do_timestamp )
        self.toFrontend(source, name)
    def toFrontend(self, source):
        self.source=source


class GraphSource(Source, Constrained_Machine):
    """
    Source Machine Hybrid.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name="Source", colors=None):
        Source.__init__(self, context=context, init_n = 0, intensity = 10, weights = None )
        Constrained_Machine.__init__(self, context=context, name=name)
        self.colors=colors
    def send_requests(self, dst):
        while True:
            new_request, delta_t = self.generate_request()
            new_request.__class__=FrontendRequest
            new_request.toFrontend(source=self.name)
            yield self.env.timeout(delta_t)
            self.send_request(dst, new_request)
            if self.colors:
                self.colors.set_color(self.name, dst.name, "red")

def  webSearch(graphing):
    # Simulation parameters
    num_backend_servers = 5
    num_frontend_servers =2
    backend_catalog_size = 10
    frontend_catalog_size = 100
    verbose = True
    simulated_time = 100000
    num_sources=3

    # Create a common context
    env = simpy.Environment()

    print("Initialize catalog...")
    backend_catalog = build_catalog(frontend_catalog_size)
    frontend_catalog = build_job_catalog(backend_catalog_size)

    monitor = Monitor(env) # keeps metrics
    frontend_ctx = Context( env, monitor, frontend_catalog)
    backend_ctx = Context( env, monitor, backend_catalog)

    # Create request processing machines
    backend_servers = []
    frontend_servers=[]
    print("Initialize backend Servers...")

    for i in range(num_backend_servers):
        s = BackendServer(name=f"Backend_{i}", context = backend_ctx, bandwidth = 10, space_capacity=10, verbose=verbose)
        backend_servers.append(s)

    print("Initialize frontend Servers...")

    for i in range(num_frontend_servers):
        s = FrontendServer(name=f"Frontend_{i}", context = frontend_ctx, bandwidth = 10, space_capacity=10, verbose=verbose)
        frontend_servers.append(s)


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
        src = GraphSource(context= frontend_ctx, intensity = 10, name="Source_"+str(s))
        env.process(src.send_requests(load_balancer))
        sources.append(src)

    for f in frontend_servers:
        f.backend_servers=backend_servers
        f.update_source_list(sources)

    for b in backend_servers:
        b.update_frontend_server_list(frontend_servers)


    Controller(frontend_ctx, frontend_allocator, load_balancer, verbose = verbose)
    Controller(backend_ctx, backend_allocator, dummy_router, verbose = verbose)
    # Let's go!
    if graphing:
        graph(frontend_servers, backend_servers, sources, load_balancer, env)

    print("Run sim...")
    start = time.time()
    env.run(until=simulated_time)
    print("Simulation finished!\n")
    # Print stats
    print("data: ", monitor.data)
    if verbose:
        print("data by name: ", monitor.data_by_name)
        for f in frontend_servers:
            print (f.name, "full completed requests: ", f.complete_requests)
    elapsed_time = time.time() - start
    total_requests=sum([src.n for src in sources])

    print("elapsed real time:", elapsed_time, " simulated ", total_requests, " requests. ( ", total_requests/elapsed_time,"reqs/s)")
    print()


if __name__ == "__main__":
    graphing=False
    if len(sys.argv)>1:
        if  (not "-g" in sys.argv):
            raise ValueError("Not a valid parameter. Please use -g to visualize system.")
        if ("-g" in sys.argv):

            from graphing.webSearchGraph import *
            graphing=True

    webSearch(graphing)
