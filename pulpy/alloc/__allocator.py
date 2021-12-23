from .allocation_map import AllocationMap

class Allocator(object):
    # Extensible component responsible for allocating items to machines.
    def __init__(self, machines, catalog, verbose = False):
        self.machines=machines
        self.catalog=catalog
        self.allocation_map=AllocationMap()
        self.verbose = verbose

    def get_current_allocation(self):
        # Use in case of getting out of sync
        allocation_map = AllocationMap()
        for m in self.machines:
            for item in m.get_memory():
                allocation_map.allocate(item, m)
        return allocation_map

    def compute_allocation(self):
        allocation_map=AllocationMap()
        budget = {m:m.capacity for m in self.machines}
        for item in self.catalog.get_iterator():
            allocated = False
            if not budget:
                break
            for m in list(budget.keys()):
                if item.work <= budget[m]:
                    budget[m] -= item.work
                    if budget[m] <=0:
                        del budget[m]
                    allocation_map.allocate(item, m)
                    allocated = True
                    break
            if not allocated and self.verbose:
                print("Could not find spot for item ", item.name,  " and size ", item.work)

        if self.verbose:
            allocation_map.print_allocations()
        return allocation_map

    def allocate_update(self, new_alloc_map):
        # allocate assuming machines are already provisioned.

        partial_map = AllocationMap()
        for machine in new_alloc_map.alloc.keys():
            # define sets:
            final = set(new_alloc_map.alloc[machine])
            initial = set(machine.get_memory())
            to_evict = initial.difference(final)

            # Clean up
            [machine.evict(item) for item in to_evict]

            # New
            for item in new_alloc_map.alloc[machine]:
                result = machine.fetch(item)
                if result.result in [0,3]:   #0 is success, 3 is already in memory
                    partial_map.allocate(item, machine)

        if partial_map == new_alloc_map:
            success = True
        else:
            success = False

        self.allocation_map = partial_map
        return (success, self.allocation_map)
