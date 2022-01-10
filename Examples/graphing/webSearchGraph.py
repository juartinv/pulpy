
import networkx as nx
import matplotlib.pyplot as plt
grey= (.33,.33,.33, .2)

def graph(frontend_servers, backend_servers, sources, load_balancer, env):
    """
    Set up everything to graph system.
    """
    frontend_server_horizontal_positon= 4
    source_horizontal_positon=2
    load_balancer_horizontal_positon=3
    backend_server_horizontal_positon=5
    vertical_size_scalar=4
    pos={}
    g=nx.Graph()
    color_choice=["r", "b", "g"]

    top=max(len(frontend_servers), len(backend_servers), len(sources))

    for f, frontend in enumerate(frontend_servers):
        g.add_edge(frontend.name, load_balancer.name)
        pos[frontend.name]=(frontend_server_horizontal_positon, f*vertical_size_scalar)

    pos[ load_balancer.name]=(load_balancer_horizontal_positon, 0)
    for s, source in enumerate(sources):
        for f in frontend_servers:
            g.add_edge(source.name, f.name)
        g.add_edge(source.name, load_balancer.name)
        pos[source.name]=(source_horizontal_positon, (top-s)*vertical_size_scalar)

    for b, backend in enumerate(backend_servers):
        for f, frontend in enumerate(frontend_servers):
            g.add_edge(frontend.name, backend.name)
        pos[backend.name]=(backend_server_horizontal_positon, b*vertical_size_scalar)

    colors=Colors(g)
    for frontend in frontend_servers:
        frontend.set_graphing(colors=colors, load_balancer=load_balancer)
    for source in sources:
        source.colors=colors


    update_graph(frontend_servers, backend_servers, sources, load_balancer, pos, g, colors.get_colors())
    graphing=GraphMaker(env, g, frontend_servers, backend_servers, load_balancer, sources, pos, colors)
    env.process(graphing.run())


def update_graph(frontend_servers, backend_servers, sources, load_balancer, pos, g, colors=[], title=" "):
    plt.clf()
    nx.draw_networkx_nodes(g, pos, nodelist=[n.name for n in frontend_servers], node_color="green")
    nx.draw_networkx_nodes(g, pos, nodelist=[n.name for n in backend_servers], node_color="blue")
    nx.draw_networkx_nodes(g, pos, nodelist=[s.name for s in sources], node_color="red")
    nx.draw_networkx_nodes(g, pos, nodelist=[load_balancer.name], node_color="yellow")
    nx.draw_networkx_labels(g, pos, font_size=8)
    plt.title("Time "+ title)
    if colors==[]:
        colors=[grey]* len(g.edges)

    nx.draw_networkx_edges(g, pos, edgelist=g.edges, edge_color=colors, width=1 )

    plt.axis('off')
    plt.tight_layout()
    plt.draw()
    plt.pause(.003)


class Colors():
    """
    Keeps track of which color which link should be for graphing.
    """
    def __init__(self, g):
        self.g=g
        self.colors=[[grey]]* len(self.g.edges())

    def update(self):
        for c , colors in enumerate(self.colors.copy()):
            tmp =colors
            if len(colors)<=1:
                self.colors[c]=[grey]
                assert([grey]==self.colors[c])
            else:
                self.colors[c]=colors[1:]
                assert(tmp!=self.colors[c])
            assert(len(self.colors[c])!=0)
    def set_color(self, A, B, color):
        for l, link in enumerate(self.g.edges()):
            if A in link and B in link:
                if (len(self.colors[l])<1) or (not self.colors[l][-1]==color):
                    self.colors[l].append(color)
                if self.colors[l][0]==grey and len(self.colors[1])>1:
                    self.colors[l].pop(0)
                return
        else:
            raise ValueError("Could not find link ", A, B, " in ", self.g.edges)

    def get_colors(self):
        return [c[0] for c in self.colors]

    def updated(self):
        if len([c[0] for c in self.colors if (not c[0]==self.colors[0][0]) and (not c[0]=="red")])>=1:
            return 1
        else:
            0

class GraphMaker():
    """
    Uses the updated color object from the frontend_servers to update graph.
    """
    def __init__(self, env, g, frontend_servers, backend_servers, load_balancer, sources, pos, colors ):
        self.env= env
        self.g=g
        self.frontend_servers=frontend_servers
        self.backend_servers=backend_servers
        self.load_balancer=load_balancer
        self.sources=sources
        self.pos=pos
        self.colors=colors

    def run(self):
        yield self.env.timeout(.0001)
        while True:
            if self.colors.updated():
                update_graph(self.frontend_servers, self.backend_servers, self.sources, self.load_balancer, self.pos, self.g, colors=self.colors.get_colors(), title=str(self.env.now))
            self.colors.update()
            yield self.env.timeout(.03)
