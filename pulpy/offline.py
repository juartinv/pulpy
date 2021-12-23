import random
import simpy
from pulpy.system import *
from pulpy.machines import Router
from pulpy.fun import *
from pulpy.alloc import Allocator


class Controller(object):
    """
    Controls the system's components.
    """
    def __init__(self, context, allocator, router, verbose = True, how_often = 10):
        self.context = context
        self.env= context.env
        self.monitor=context.monitor
        self.verbose = verbose
        self.how_often = how_often

        # assert interfaces
        assert isinstance(allocator, Allocator)
        self.allocator = allocator

        assert isinstance(router, Router)
        self.router = router

        self.action = self.env.process(self.run())

    def run(self):
        # Orchestrates interaction between offline components
        yield self.env.timeout(1)

        while True:
            yield self.env.timeout(self.how_often)
            allocation_map = self.allocator.compute_allocation()
            success, actual_allocation_map = self.allocator.allocate_update(allocation_map)
            if success:
                if self.verbose:
                    print_green("---- ALLOCATION SUCCESSFUL!!")
            elif self.verbose:
                print_red("---- ALLOCATION FAILED!!!!")
                print("intended:")
                allocation_map.print_allocations()
                print("got:")
                actual_allocation_map.print_allocations()
            self.router.push_alloc_map(actual_allocation_map)
