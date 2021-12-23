
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
