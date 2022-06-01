import simpy
import random, time
import sys
import networkx as nx
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator
import numpy as np
grey= (.33,.33,.31)

class Edge_tracker():
    def __init__(self, g, env):
        self.g=g
        self.buffers=dict()
        self.env=env
        self.build_buffers()


    def build_buffers(self):
        for n in self.g.edges:
            self.buffers[n]=Buffer(env=self.env)


    def clean(self):
        for n in self.buffers:
            self.buffers[n].buffer_clean()

    def get_colors(self, path=[]):
        colors={}
        path_edges=[]
        for i , e in enumerate(path):
            if not i==len(path)-1:
                if (path[i], path[i+1]) in self.buffers:
                    path_edges.append((path[i], path[i+1]))
                elif (path[i+1], path[i]) in self.buffers:
                    path_edges.append((path[i+1], path[i]))
        for n in self.buffers:
            if n not in path_edges:
                w=self.buffers[n].get_buffer_len()
                self.g.edges[n]["weight"]=sum([_n.buffer.get_buffer_len() if not _n.name =="Client" else 100 for _n in n ])
                colors[n]=w
            else:
                colors[n]="yellow"
        return colors

    def add_to_buff(self,a,b, request):
        if len(self.buffers)<=0:
            self.build_buffers()
        #print(self.g.edges)
        for e in self.buffers:
            if a in e and b in e:
                self.buffers[e].buffer_add(request)
                break
        else:
            raise ValueError("Could not find edge")

class Buffer():
    def __init__(self, env, buffer_time=10):
        self.buffer={}
        self.buffer_time=buffer_time
        self.env=env
    def buffer_add(self, request):

        if not int(self.env.now) in self.buffer:
            self.buffer[int(self.env.now)]=[]
        self.buffer[int(self.env.now)].append(request)

    def get_buffer_len(self):
        self.buffer_clean()
        i=0
        for t in self.buffer:
            i+=len(self.buffer[t])
        return i
    def buffer_clean(self):
        for time in self.buffer.copy():
            if time< (self.env.now-self.buffer_time):
                del self.buffer[time]

class label_stacking(Constrained_Machine):
    """

    """
    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, g=None, client=None, edge_tracker=None):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.name=name
        self.client =client
        self.g=g
        self.edge_tracker=edge_tracker
        if ("switch" in self.name):
            self.switch=True
        else:
            self.switch=False
        self.neighbors=[]#nx.neighbors(self.g, self)

        self.buffer=Buffer(env=self.env)
        self.n=0
        #Below are only necesary if you are graphing the system
        self.colors=None



    def _admission_control(self, request):
        self.buffer.buffer_add(request)
        request.finish_callback=self.pass_request(request)


    def pass_request(self, request):
        """

        """
        if self.verbose:
            pass
        if len(request.labels)==0:
            self.return_packet(request)
            return
        dst=request.labels[0]
        request.labels=request.labels[1:]
        if dst not in self.neighbors:
            print ([n.name for n in self.neighbors])
            print([r.name for r in request.labels])
            print(dst.name, self.name)
            raise ValueError("Label given for non existant neighbor")
        else:
            self.edge_tracker.add_to_buff(self, dst, request)
            dst.add_request(request)



    def return_packet(self, request):
        request.direction= (request.direction+ 1) % 2
        request.labels= generate_labels(self.g, self, self.client)[1:]



    def set_graphing(self, colors, load_balancer):
        """
        Tell server to update values for graph.
        """
        self.colors=colors
        self.load_balancer=load_balancer

    def update_graph(self):
        """
        Update graph colors depending on where the request came from.
        """

        return self.buffer.get_buffer_len()

def generate_labels(g, start, end):
    paths= [i for i in nx.all_shortest_paths(g, start, end)]
    i= random.randint(0, len(paths)-1)
    return paths[i]


class LabelStackingRequest(Request):
    """
    src routing label stacking
    """
    def __init__( self,env, n=0, item=None, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, name=None, labels=[], direction=1):
        super().__init__(env, n, item, cli_proc_rate , cli_bw , do_timestamp )
        self.toLabelStacking(labels, direction)

    def toLabelStacking(self, labels,direction):
        self.labels=labels
        self.direction=direction

class Client(Source, Constrained_Machine):
    """
    Source Machine Hybrid.
    """
    def __init__(self, context, init_n = 0, intensity = 100, weights = None, name="Client", colors=None, g=None, servers=[], edge_tracker=None):
        Source.__init__(self, context=context, init_n = 0, intensity = 10, weights = None )
        Constrained_Machine.__init__(self, context=context, name=name)
        self.colors=colors
        self.g=g
        self.name=name
        self.servers=servers
        self.weights=[]
        self.set_weights(0)
        self.A=None
        self.B=None
        self.edge_tracker=edge_tracker

    def find_A_and_B(self):
        for n in self.g.nodes:
            if n.name=="server_0":
                self.A= n
            elif n.name=="server_8":
                self.B=n

    def find_path(self):
        self.edge_tracker.get_colors()
        if not self.A and not self.B:
            self.find_A_and_B()
        if self.A and self.B:
            path=nx.shortest_path(self.g, source= self.A, target=self.B, weight='weight')
            return path
        else:
            print (self.A, self.B)
            raise ValueError
    def set_weights(self, r):
        if len (self.servers)>0:
            i=int(self.env.now)%len(self.servers)

            self.weights=[1]* len(self.servers)
            self.weights[r]+=50*(i+1)
            self.weights[i%len(self.servers)]+=i
            self.weights[-1]+=3*i
            self.weights[i]+=10
            self.weights[int(len(self.weights)/2)]+=6
            self.weights[(int(len(self.weights)/2)-1)%len(self.servers)]+=4
            self.weights[(int(len(self.weights)/2)+1)%len(self.servers)]+=5
            self.weights=[s/sum(self.weights) for s in self.weights]

    def send_requests(self):
        while True:
            r=random.randint(0, len(self.servers)-1)
            for i in range(0,100):
                self.set_weights(r)
                new_request, delta_t = self.generate_request()
                new_request.__class__=LabelStackingRequest

                s= np.random.choice(a=self.servers, p=self.weights)
                labels=generate_labels(self.g, self, s)
                dst=labels[1]
                labels=labels[2:]
                new_request.toLabelStacking(labels, direction=1)
                self.edge_tracker.add_to_buff(self, dst, new_request)
                dst.add_request(new_request)
                yield self.env.timeout(delta_t)

def get_graph_weights(g):
    for node in g.nodes:
        if node.name=="Client":
            continue


def DC(graphing):
    # Simulation parameters
    levels=4
    width=6
    assert(width%2 ==0)
    catalog_size = 100
    verbose = True
    simulated_time = 100000

    # Create a common context
    env = simpy.Environment()

    print("Initialize catalog...")
    catalog = build_catalog(catalog_size)
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    # Create request processing machines
    servers = []
    switches=[]
    server_ratio=2
    g=nx.Graph()
    edge_tracker=Edge_tracker(g=g, env=env)
    client= Client( context= ctx, g=g, servers=[], edge_tracker=edge_tracker)
    pos={}
    spacing_h=4
    spacing_v=4
    print("Initialize Switches..")
    for l in range(levels):
        for i in range(width):
            s = label_stacking(context= ctx, name="switch_"+str(width*(l)+i),  client=client, g =g, edge_tracker=edge_tracker)
            switches.append(s)
            pos[s]=[ (i+1)*spacing_h , (2+levels-l)*spacing_v]
            if l==0:
                g.add_edge(s, client)
            else:
                g.add_edge(switches[-(width+1)], switches[-1])
                if i<width-1:
                    g.add_edge(switches[-(width)], switches[-1])
                if i>0:
                    g.add_edge(switches[-(width+2)], switches[-1])
            if l==levels-1:
                for b in range(server_ratio):
                    server=label_stacking(context= ctx, name="server_"+str((i*server_ratio)+b),client=client, g =g, edge_tracker=edge_tracker)
                    g.add_edge(s, server)
                    servers.append(server)
                    pos[server]=[ (i )*spacing_h + ((b+1.5) * (spacing_h/server_ratio)) , (1)*spacing_v]

    client.servers=servers
    pos[client]=[((width+1)*spacing_h)/2 , (levels+3) * spacing_v]
    for s in switches:
        s.neighbors=list(nx.neighbors(g, s))

    env.process(client.send_requests())

    # Let's go!
    if graphing:
        graph(env, g, pos, edge_tracker)
    assert (len(edge_tracker.g.nodes)!=0)

    print("Run sim...")
    start = time.time()
    env.run(until=simulated_time)
    print("Simulation finished!\n")

if __name__ == "__main__":
    graphing=False
    if len(sys.argv)>1:
        if  (not "-g" in sys.argv):
            raise ValueError("Not a valid parameter. Please use -g to visualize system.")
        if ("-g" in sys.argv):
            from graphing.eulerGraph import *
            graphing=True

    DC(graphing)
