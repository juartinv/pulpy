
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

cmap = matplotlib.cm.get_cmap('Blues')
scaler=10
grey= (.33,.33,.33, .2)

def graph(env, g, pos, edge_tracker):
    """
    Set up everything to graph system.
    """
    update_graph( g=g, colors=[], pos=pos, edge_tracker=edge_tracker)
    graphing=GraphMaker(env, g, pos, edge_tracker)
    env.process(graphing.run())

def update_graph(pos, g, colors=[], title=" ", edge_tracker=None, ax=None,labels=None, path=None, outline_colors=None):
    plt.clf()
    colors=[]
    for s in g.nodes:
        if not s.name=="Client":
            colors.append(cmap(s.update_graph()*scaler))
        else:
            colors.append(grey)
            path=s.find_path()
    #print(len(path))
    outline_colors=[]
    outline_widths=[]
    for i, s in enumerate(g.nodes):
        if s in path:
            outline_colors.append("yellow")
            outline_widths.append(4)
        else:
            outline_colors.append("white")
            outline_widths.append(0)



    if colors==[]:
        colors=[grey]* len(g.nodes)
        colors=[grey]


    nodes=nx.draw_networkx_nodes(g, pos, nodelist=g.nodes,  node_color=colors, linewidths=outline_widths)

    if labels:
        nx.draw_networkx_labels(g, pos, labels, font_size=22, font_color="red")

    edge_tracker_colors=edge_tracker.get_colors(path)

    edge_colors= [cmap(edge_tracker_colors[e]*scaler) if not edge_tracker_colors[e] =="yellow" else edge_tracker_colors[e] for e in edge_tracker_colors]

    #plt.title("Time "+ title)
    nx.draw_networkx_edges(g, pos, edgelist=g.edges, edge_color=edge_colors, width=1 )
    if outline_colors:
        nodes.set_edgecolor(outline_colors)
        #nodes.set_edgewidth(outline_widths)
    plt.axis('off')
    plt.tight_layout()
    if ax:

        ax.annotate('Midici', xy=list(pos.values())[0], xytext=list(pos.values())[0],
            textcoords='offset points',
            color='b', size='large',
            arrowprops=dict(
                arrowstyle='simple,tail_width=0.3,head_width=0.8,head_length=0.8',
                facecolor='b', shrinkB=4 * 1.2)
                )
    #plt.gcf().canvas.draw_idle()
    plt.draw()
    plt.pause(.003)
    #plt.gcf().canvas.start_event_loop(2)

class GraphMaker():
    """
    Uses the updated color object from the frontend_servers to update graph.
    """
    def __init__(self, env, g, pos, edge_tracker):
        plt.ion()
        self.env= env
        self.g=g
        self.pos=pos
        self.colors={}
        self.labels={}
        self.edge_tracker=edge_tracker
        for n in self.g.nodes:
            if n.name=="server_0":
                self.A= n
                self.labels[n]="A"
            elif n.name=="server_8":
                self.B=n
                self.labels[n]="B"
            else:
                self.labels[n]=""
        self.ax = plt.gca()
    def run(self):
        yield self.env.timeout(100)
        while True:
            update_graph(g=self.g, pos=self.pos, title=str(self.env.now)[:3], edge_tracker=self.edge_tracker, ax=self.ax, labels=self.labels)
            yield self.env.timeout(1)
