import simpy
import random, time

import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import RouterLeastCongested,  Constrained_Machine
from pulpy.offline import Controller
from pulpy.alloc import Allocator

import matplotlib.pyplot as plt
import numpy as np

class shower_Manager(Constrained_Machine):
    """
    Sets a randome temperature for its "shower".
    Waits for a response to increase or decrease the temperature.
     """
    def __init__(self, name, context,  bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, id=0,  max_temp=70, min_temp=-10):
        super().__init__( name, context, bandwidth, hard_limit_concurrency, space_capacity)
        self.verbose= verbose
        self.name
        assert(min_temp< max_temp)
        self.max_temp=max_temp
        self.min_temp=min_temp
        self.window=[self.min_temp, self.max_temp]
        self.current_temp=random.randint(self.min_temp, self.max_temp)


    def _admission_control(self, request):
        super()._admission_control(request)
        self.adjust_temperature(request.instructions)

    def reset_window(self):
        self.window=[self.min_temp, self.max_temp]

    def adjust_temperature(self, instructions):

        if instructions=="+":
            if self.current_temp>=self.window[1]:
                #self.window[1]=random.randint(self.window[0]+2, self.max_temp)
                self.window[1]+=1
            self.window[0]=self.current_temp
            overshoot=random.randint(0,5)

        elif instructions=="-":
            if self.current_temp<=self.window[0]:
                self.window[0]-=1
            self.window[1]=self.current_temp
            overshoot=random.randint(-5,0)

        #self.current_temp=random.randint(*self.window)
        self.current_temp=int(self.window[0]+(self.window[1]- self.window[0])/2) +overshoot

class graphing_shower_Manager(shower_Manager):
    def __init__(self, name, context, shower_Managers, shower_Users, fig, plt, bandwidth = 1.0,  hard_limit_concurrency = 20, space_capacity = 10, verbose=True, id=0, max_temp=70, min_temp=-20):
        super.__init__( name, context,  bandwidth ,  hard_limit_concurrency , space_capacity , verbose, id,  max_temp, min_temp)
        self.tographing(shower_Managers, shower_Users)

    def tographing(self, shower_Managers, shower_Users, fig, ax):
        self.shower_Managers=shower_Managers
        self.shower_Users=shower_Users
        self.fig=fig
        self.ax=ax

    def adjust_temperature(self, instructions):
        super().adjust_temperature(instructions)
        self.fig.clear()

        update_graph(self.fig, self.ax, self.shower_Managers, self.shower_Users)

class showerRequest(Request):
    """
    Request to increase or decrease shower temperature.
    """
    def __init__(self,env, n=0, item=None, cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, instructions="="):
        super().__init__(env, n, Item(name="temp_adjust", work=1, size=0), cli_proc_rate , cli_bw, do_timestamp)
        self.instructions=instructions

class shower_User(ContextUser, CoreRequestSource):
    """
    Uses the shower. has an ideal temperature that the user wants to convey to the shower manager.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name=None, prefered_temperature=40, showers=[]):
        ContextUser.__init__(self, context)
        CoreRequestSource.__init__(self, init_n = init_n)
        self.prefered_temperature=prefered_temperature
        self.name=name
        self.showers=showers
        print ("Starting shower user,", name, "with a preffered temperature of",  prefered_temperature, "who is using", len(showers), "showers : ", [shower.name for shower in self.showers])

    def adjust_temperature(self, shower):
        if shower.current_temp>self.prefered_temperature:
            instructions="-"
        else:
            instructions="+"
        new_request=showerRequest(env=self.env, n=self.n,  instructions=instructions)
        self.n+=1
        self.send_request(shower, new_request)

    def send_requests(self):
        while True:
            for s in self.showers:
                if not s.current_temp==self.prefered_temperature:
                    self.adjust_temperature(s)
            yield self.env.timeout(1)

def update_graph(fig, ax, shower_Managers, shower_Users):


    ind=np.arange(len(shower_Managers))
    p1 = plt.bar(ind, [s.current_temp for s in shower_Managers])
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
    plt.tight_layout()
    plt.draw()
    plt.pause(0.0001)


def make_Shower_system(env, ctx, num_shower_Managers, num_shower_Users, verbose):

    # Create request processing machines

    shower_Managers = []

    for i in range(num_shower_Managers):
        s = shower_Manager(name=i,  context = ctx, bandwidth = 10, space_capacity=10)
        shower_Managers.append(s)

    # Generate shower users
    shower_Users=[]
    for User in range(num_shower_Users):
        amount_of_showers=random.randint(1, len(shower_Managers))
        user_showers= random.choices(shower_Managers, k=amount_of_showers)
        prefered_temperature= random.randint(20, 50)
        #prefered_temperature=40
        user= shower_User(context = ctx, name=User, intensity = 10, showers=user_showers, prefered_temperature=prefered_temperature)

        # instruct the source to send its requests to the load balancer
        env.process(user.send_requests())
        shower_Users.append(user)
    fig, ax = plt.subplots()
    update_graph(fig, ax, shower_Managers, shower_Users)
    for manager in shower_Managers:
        manager.__class__=graphing_shower_Manager
        manager.tographing(fig=fig, ax=ax, shower_Managers=shower_Managers, shower_Users=shower_Users)
    return shower_Managers, shower_Users


def  shower():

    # Simulation parameters
    num_shower_Managers=10
    num_shower_Users=10

    verbose = True
    simulated_time = 1



    # Create a common context
    env = simpy.Environment()
    catalog = Catalog()
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    #Generate oneHop system
    showers, shower_Users=make_Shower_system(env, ctx, num_shower_Managers, num_shower_Users, verbose=verbose)
    for shower in showers:
        print(shower.name, shower.current_temp)
    # Let's go!
    print("Run sim...")
    start = time.time()
    env.run(until=simulated_time)
    print("Simulation finished!\n")
    for shower in showers:
        print(shower.name, shower.current_temp, shower.window)
    # Print stats
    elapsed_time = time.time() - start
    total_requests=sum([src.n for src in shower_Users])
    print("elapsed real time:", elapsed_time, " simulated ", total_requests, " requests. ( ", total_requests/elapsed_time,"reqs/s)")
    print()

if __name__ == "__main__":
    shower()
