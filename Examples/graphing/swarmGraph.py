import matplotlib.pyplot as plt
import numpy as np
import sys
sys.path.append("./../")
from swarm import Bird

class GraphMaker():
    """

    """
    def __init__(self, env , birds ):
        self.env= env
        fig, ax = plt.subplots()
        self.fig=fig
        self.ax=ax
        self.birds=birds
        self.locations=Locations(self.birds)
        update_graph(self.fig, self.ax, birds= self.birds, locations=self.locations.get_locations(),  title= "Time "+str(self.env.now))
        for bird in self.birds:
            bird.__class__=graphing_Bird
            bird.tographing(self.locations)

    def run(self):
        yield self.env.timeout(.0001)
        while True:
            if self.locations.updated:
                self.fig.clear()
                update_graph(self.fig, self.ax, birds=self.birds, locations=self.locations.get_locations(), title= "Time "+str(self.env.now))
                self.locations.update()
            yield self.env.timeout(.03)

class Locations():
    """
    Keeps track of Locations for graphing
    """
    def __init__(self, birds):
        self.birds=[b.name for b in birds]
        self.locations=[[[b.x, b.y]] for b in birds]
        self.updated=0
    def update(self):
        for l , location in enumerate(self.locations.copy()):
            if len(location)>1:
                self.locations[l].pop(0)
    def set_location(self, name, location):
        if name in self.birds:
            self.locations[self.birds.index(name)].append(location)
            self.updated=1
        else:
            raise ValueError("Could not find ", name , " in ", self.birds)

    def get_locations(self):
        return ([b[0][0] for b in self.locations], [b[0][1] for b in self.locations])



class graphing_Bird(Bird):
    """
    A normal shower manager but it also updates the temperature graph everytime a temperature change is made.
    """
    def __init__(self, name, context, bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, id=0, max_temp=70, min_temp=-20):
        super.__init__( name, context,  bandwidth ,  hard_limit_concurrency , space_capacity , verbose, id,  max_temp, min_temp)
        self.tographing()
        self.locations=None

    def tographing(self, locations):
        self.locations=locations
        self.restricted_movement=[1000,1000]


    def adjust_temperature(self, instructions):
        super().adjust_temperature(instructions)
        self.temperatures.set_temp(self.name, self.current_temp)

def update_graph(fig, ax, birds, locations, title=""):
    """
    Updates the location graph.
    """

    p1 = plt.scatter(*locations)
    plt.axhline(0, color='grey', linewidth=0.8)
    ax.set_ylabel(' ')
    ax.set_xlabel(' ')
    #ax.set_xticks(ind)
    #ax.set_xticklabels([s.name for s in shower_Managers])

    colors=["blue", "red", "yellow", "green", "black", "indigo", "darkred", "lime", "seagreen", "pink"]

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Prefered Temperatures")
    plt.ylim(0, 1000)
    plt.xlim(0, 1000)
    plt.title(title)
    plt.tight_layout()
    plt.draw()
    plt.pause(0.000001)
