
class AllocationMap(object):
    # Keeps track of item allocation to caches.
    def __init__(self):
        self.alloc_o = dict()  #  for each item (key) maps a list of caches where it is cached. Has entries just for allocated objects.
        self.alloc = dict()    #  for each cache (key) maps the list of items it caches (the cache.cache)

    def allocate(self, item, cache):
        if item not in self.alloc_o.keys():
            self.alloc_o[item] = []
        self.alloc_o[item].append(cache)
        if cache not in self.alloc.keys():
            self.alloc[cache] = []
        self.alloc[cache].append(item)

    def evict(self, item, cache):
        if item not in self.alloc_o.keys():
            return "item not allocated"
        if cache not in self.alloc.keys():
            return "unknown cache"
        if item not in self.alloc_o[cache] or cache not in self.alloc[item]:
            return "item not allocated to cache"

        self.alloc[cache].remove(item)
        if not len(self.alloc[cache]):
            del self.alloc[cache]

        self.alloc_o[item].remove(cache)
        if not len(self.alloc_o[item]):
            del self.alloc_o[item]

    def print_allocations(self):
        print ("_______________________________")
        print ("Computed Cache Allocations")
        for cache in self.alloc:
            print ("cache: ", cache.name, " cache filled: " , sum([j.work for j in self.alloc[cache]]), "/",  cache.capacity)
            for item in self.alloc[cache]:
                print (item.name, " size: ", item.work)
        print ("_______________________________")

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        if set(self.alloc.keys()) != set(other.alloc.keys()):
            return False

        if set(self.alloc_o.keys()) != set(other.alloc_o.keys()):
            return False

        for k,v in self.alloc.items():
            if set(v).difference(set(other.alloc[k])):
                return False

        for k,v in self.alloc_o.items():
            if set(v).difference(set(other.alloc_o[k])):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)



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
