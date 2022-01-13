import simpy
import random, time

import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import Router,  Machine
from pulpy.offline import Controller



class Bird(Machine):
    """
    Source Machine Hybrid.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name="Bird", x=None, y=None, direction=None, restricted_movement=None):
        Machine.__init__(self, name, context)
        self.dst=None
        if x==None:
            self.x=random.randint(0, 1000)
        else:
            self.x=x
        if y==None:
            self.y=random.randint(0, 1000)
        else:
            self.y=y
        if direction==None:
            self.direction=[float(random.randint(0, 1000))/1000.0, float(random.randint(0, 1000))/1000.0]
        else:
            self.direction=direction
        self.sight=5 #How far away can two birds be when communicating
        self.call_frequency=20# percent of time Bird is calling
        self.interval=.1
        self.n=0
        if restricted_movement:
            self.restricted_movement=restricted_movement
        self.locations=None #for graphing
    def call(self):
        self.n += 1
        new_call = Call(self.env, self.n, x=self.x, y=self.y, direction=self.direction)
        self.dst.add_request(new_call)

    def swarm(self, dst):
        self.dst=dst
        while True:
            if random.randint(0,100)<=self.call_frequency:
                self.call()
            self.move()
            yield self.env.timeout(self.interval)

    def move(self):

        new_y=self.y+self.direction[1]
        new_x=self.x+self.direction[0]

        if self.restricted_movement:
            if new_y>self.restricted_movement[1] or new_y<0:
                new_y=self.y-self.direction[1]
            if new_x>self.restricted_movement[0] or new_x<0:
                new_x=self.x-direction[0]

        self.x=new_x
        self.y=new_y

        if self.locations:#update for graph
            self.locations.set_location( self.name, [self.x, self.y])


    def _admission_control(self, request):
        super()._admission_control(request)
        #Adapt behavior
        self.Join(request)

    def Join(self, request):
        self.direction=( request.x-self.x, request.y, self.y)

class Call(Request):
    """

    """
    def __init__(self,env, n=0, item=Item(name="Call", work=1, size=1, life_cycle = 1), cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, x=0, y=0, direction=[0,0]):
        super().__init__(env, n, item, cli_proc_rate , cli_bw, do_timestamp)
        self.x=x
        self.y=y
        self.direction=direction

class Line_of_Sight(Router):
        def __init__(self, context, machines, name):
            Router.__init__(self, context, machines, name)

        def route_request(self, request):
            """
            Send request to every bird that is in line of sight of the requesting bird.
            """
            for bird in self.machines:
                distance= (  (bird.x-request.x)**2 +  (bird.y - request.y)**2    ) **.5
                if distance<=bird.sight:
                    bird.add_request(request)


def  swarm(graphing, c):

    # Simulation parameters
    num_birds=100

    verbose = True
    simulated_time = 10

    # Create a common context
    env = simpy.Environment()
    catalog = Catalog()
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    birds=[]
    for bird in range(num_birds):
        b= Bird(context=ctx, name="Bird_"+str(bird))
        birds.append(b)

    Sight= Line_of_Sight( context=ctx, machines=birds, name="Sight")

    for bird in birds:
        env.process(bird.swarm(Sight))

    # Let's go!
    print ("Initial Locations:")
    for bird in birds:
        print(bird.name, "Location:", bird.x, bird.y, "Direction:", bird.direction)
    print("Run sim...")

    if graphing:
         graphing= GraphMaker( env, birds)
         env.process(graphing.run())

    start = time.time()
    env.run(until=simulated_time)

    print("Simulation finished!\n")
    print ("Final Locations:")
    for bird in birds:
        print(bird.name, "Location:", bird.x, bird.y, "Direction:", bird.direction)
    # Print stats
    elapsed_time = time.time() - start
    total_requests=sum([bird.n for bird in birds])
    print("elapsed real time:", elapsed_time, " simulated ", total_requests, " requests. ( ", total_requests/elapsed_time,"reqs/s)")
    print()

if __name__ == "__main__":
    graphing=False
    c=False
    if len(sys.argv)>1:
        if  (not "-g" in sys.argv) and  (not "-c" in sys.argv):
            raise ValueError("Not a valid parameter. Please use -g to graph Temperatures and -c for shower uses to have a small range of preffered Temperatures.")
        if ("-g" in sys.argv):
            from graphing.swarmGraph import *
            graphing=True
        if ("-c" in sys.argv):
            c=True
    swarm(graphing, c)
