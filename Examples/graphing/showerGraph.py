import matplotlib.pyplot as plt
import numpy as np
import sys
sys.path.append("./../")
from shower import  shower_Manager

class GraphMaker():
    """
    Uses the updated color object from the frontend_servers to update graph.
    """
    def __init__(self, env, shower_Managers, shower_Users):
        self.env= env
        self.shower_Managers=shower_Managers
        self.shower_Users=shower_Users
        self.temperatures=Temperatures(self.shower_Managers)
        fig, ax = plt.subplots()
        self.fig=fig
        self.ax=ax
        update_graph(self.fig, self.ax, self.shower_Managers, self.shower_Users, self.temperatures.get_temps(), title= "Time "+str(self.env.now))
        for manager in self.shower_Managers:
            manager.__class__=graphing_shower_Manager
            manager.tographing(self.temperatures)

    def run(self):
        yield self.env.timeout(.0001)
        while True:
            if self.temperatures.updated:
                self.fig.clear()
                update_graph(self.fig, self.ax, self.shower_Managers, self.shower_Users, self.temperatures.get_temps(), title= "Time "+str(self.env.now))
                self.temperatures.update()
            yield self.env.timeout(.03)

class Temperatures():
    """
    Keeps track of temperatures for graphing
    """
    def __init__(self, shower_Managers):
        self.shower_Managers=[s.name for s in shower_Managers]
        self.temps=[[s.current_temp] for s in shower_Managers]
        self.updated=0
    def update(self):
        for t , temp in enumerate(self.temps.copy()):
            if len(temp)>1:
                self.temps[t].pop(0)
    def set_temp(self, name, temp):
        if name in self.shower_Managers:
            self.temps[self.shower_Managers.index(name)].append(temp)
            self.updated=1
        else:
            raise ValueError("Could not find ", name , " in ", self.shower_Managers)

    def get_temps(self):
        return [t[0] for t in self.temps]



class graphing_shower_Manager(shower_Manager):
    """
    A normal shower manager but it also updates the temperature graph everytime a temperature change is made.
    """
    def __init__(self, name, context, temperatures, bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, id=0, max_temp=70, min_temp=-20):
        super.__init__( name, context,  bandwidth ,  hard_limit_concurrency , space_capacity , verbose, id,  max_temp, min_temp)
        self.tographing(temperatures)

    def tographing(self, temperatures):
        self.temperatures=temperatures

    def adjust_temperature(self, instructions):
        super().adjust_temperature(instructions)
        self.temperatures.set_temp(self.name, self.current_temp)

def update_graph(fig, ax, shower_Managers, shower_Users, temperatures, title=""):
    """
    Updates the temperature graphs.
    """
    ind=np.arange(len(shower_Managers))
    p1 = plt.bar(ind, temperatures)
    plt.axhline(0, color='grey', linewidth=0.8)
    ax.set_ylabel('Temperature')
    ax.set_xlabel('Showers')
    ax.set_xticks(ind)
    ax.set_xticklabels([s.name for s in shower_Managers])

    colors=["blue", "red", "yellow", "green", "black", "indigo", "darkred", "lime", "seagreen", "pink"]

    for u , user in enumerate(shower_Users):
        for indx, i in enumerate(user.showers):
            if indx==0:
                plt.plot([i.name-.5, i.name+.5], [user.prefered_temperature, user.prefered_temperature], label="User"+str(u), color=colors[u%len(colors)])
            else:
                plt.plot([i.name-.5, i.name+.5], [user.prefered_temperature, user.prefered_temperature], color=colors[u%len(colors)])

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Prefered Temperatures")
    plt.ylim(-40, 80)
    plt.title(title)
    plt.tight_layout()
    plt.draw()
    plt.pause(0.000001)
