import simpy
import random, time
import math
import sys
sys.path.append("./../")
from pulpy.system import *
from pulpy.machines import Router,  Machine
from pulpy.offline import Controller


FIELD_SIZE=10000
class Bird(Machine):
    """
    Represents bird in a 2d plain.
    """
    def __init__(self, context, init_n = 0, intensity = 10, weights = None, name="Bird", x=None, y=None, direction=None, restricted_movement=None, behavior="f"):
        Machine.__init__(self, name, context)
        self.dst=None
        self.sight=random.randint(400, 500) #How far away can two birds be when communicating
        self.speed_limit=random.randint(70, 100) #How fast may a bird move per time interval
        #self.call_frequency= 40# percent of time Bird is calling
        self.call_frequency=random.randint(0,100)
        self.interval=.01
        self.bird_size=2
        self.behavior=behavior
        print (self.behavior)
        assert(self.behavior in ["f", "a", "j"])  #Birds can either f: follow, a: avoid or j: join other birds
        self.n=0
        if x==None:
            self.x=random.randint(0, FIELD_SIZE)
        else:
            self.x=x
        if y==None:
            self.y=random.randint(0, FIELD_SIZE)
        else:
            self.y=y
        if direction==None:
            self.direction=[float(random.randint(-100, 100)), float(random.randint(-100, 100))]
            self.adapt_speed()
        else:
            self.direction=direction

        self.color="blue"

        self.restricted_movement=restricted_movement

        self.locations=None #for graphing

    def call(self):
        self.n += 1
        new_call = Call(self.env, self.n, x=self.x, y=self.y, direction=self.direction, source=self.name)
        self.color="red"
        self.dst.add_request(new_call)

    def swarm(self, dst):
        self.dst=dst
        while True:
            if random.randint(0,100)<=self.call_frequency:
                self.call()
            self.move()
            yield self.env.timeout(self.interval)

    def adapt_speed(self):
        speed= ((self.direction[0])**2 + (self.direction[1]**2))**.5
        if speed>self.speed_limit:
            if self.direction[0]==0:
                self.direction[1]=self.speed_limit
            elif self.direction[1]==0:
                self.direction[0]=self.speed_limit
            else:
                A= math.atan(self.direction[1]/ self.direction[0])
                self.direction[0]= math.cos(A) * self.speed_limit
                self.direction[1]= math.sin(A) * self.speed_limit


    def move(self):

        new_y=self.y+ self.direction[1]
        new_x=self.x+self.direction[0]

        if self.restricted_movement:
            if new_y>self.restricted_movement[1]:
                new_y=0+new_y-self.restricted_movement[1]
            elif new_y<0:
                new_y=self.restricted_movement[1] - new_y
            elif new_x<0:
                new_x=self.restricted_movement[0] -  new_x
            elif new_x>self.restricted_movement[0]:
                new_x=0+new_x-self.restricted_movement[0]

        self.x=new_x
        self.y=new_y

        if self.locations:#update for graph
            self.locations.set_location( self.name, [self.x, self.y, self.color])
            self.color="blue"


    def _admission_control(self, request):
        super()._admission_control(request)
        #Adapt behavior
        self.color="seagreen"
        if self.behavior=="f":
            self.Follow(request)
        elif self.behavior=="j":
            self.Join(request)
        elif self.behavior=="a":
            self.Avoid(request)

        self.adapt_speed() #stay within speed limit
    def at_same_point(self, request):
        if (request.y<= self.bird_size+ self.y and request.y>= self.y -self.bird_size)  and (request.x<= self.bird_size+ self.x and request.x>= self.x -self.bird_size) :
            return 1
        return 0
    def Follow(self, request):
        if not self.at_same_point(request):
            self.direction=[( request.x-self.x) , (request.y- self.y)]

    def Avoid(self,request):
        self.direction=[ (request.y- self.y), -1* ( request.x-self.x) ]

    def Join(self, request):
        self.direction=request.direction
        if self.at_same_point(request):
            self.direction[0]+=random.randint(self.bird_size,10* self.bird_size)
            self.direction[1]+=random.randint(self.bird_size,10 *self.bird_size)



class Call(Request):
    """

    """
    def __init__(self,env, n=0, item=Item(name="Call", work=1, size=1, life_cycle = 1), cli_proc_rate = 10000, cli_bw = 10000, do_timestamp = False, source=None, x=0, y=0, direction=[0,0]):
        super().__init__(env, n, item, cli_proc_rate , cli_bw, do_timestamp)
        self.x=x
        self.y=y
        self.direction=direction
        self.source=source

class Line_of_Sight(Router):
        def __init__(self, context, machines, name):
            Router.__init__(self, context, machines, name)

        def route_request(self, request):
            """
            Send request to every bird that is in line of sight of the requesting bird.
            """
            for bird in self.machines:
                distance= (  (bird.x-request.x)**2 +  (bird.y - request.y)**2    ) **.5
                if distance<=bird.sight and not bird.name==request.source:
                    bird.add_request(request)


def  swarm(graphing, bb):

    # Simulation parameters
    num_birds=100

    verbose = True
    simulated_time = 1000

    # Create a common context
    env = simpy.Environment()
    catalog = Catalog()
    monitor = Monitor(env) # keeps metrics
    ctx = Context( env, monitor, catalog)

    birds=[]
    for bird in range(num_birds):
        b= Bird(context=ctx, name="Bird_"+str(bird), behavior=bb)
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
         graphing= GraphMaker( env, birds, FIELD_SIZE=FIELD_SIZE)
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
    bb="f" #bird behavior
    if len(sys.argv)>1:
        if  (not "-g" in sys.argv) and  (not "-b=" in sys.argv):
            raise ValueError("Not a valid parameter. Please use -g to graph Temperatures and -c for shower uses to have a small range of preffered Temperatures.")
        if ("-g" in sys.argv):
            from graphing.swarmGraph import *
            graphing=True
        if ("-b=f" in sys.argv):
            bb="f"
        if ("-b=j" in sys.argv):
            bb="j"
        if ("-b=a" in sys.argv):
            bb="a"

    swarm(graphing, bb)
