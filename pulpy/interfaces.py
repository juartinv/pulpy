import random
import simpy
import numpy as np
from collections import OrderedDict
from pulpy.fun import *
from pulpy.alloc import AllocationMap


class ContextUser(object):
    """
    Parent of all context using objects.
    """
    def __init__(self, context):
        self.context = context
        self.env = context.env
        self.monitor=context.monitor
        self.catalog = context.catalog

class DefaultContextUser(ContextUser):
    """
    A smart context user, automaticalli injecting a predefined default context.
    """
    default_context = None
    
    def __init__(self):
        if DefaultContextUser.default_context == None:
            raise Exception("Undefined default context. Call DefaultContextUser.set_default_context first.")
        super().__init__(DefaultContextUser.default_context)

    def set_default_context(context):
        DefaultContextUser.default_context = context

class Observer():
    """
    Implements Observer pattern. Abstract class.
    """

    def __init__(self):
        raise NotImplementedError

    def update(self, *obj, **kwargs):
        # abstract method
        raise NotImplementedError

class Observable(object):
    """
    Parent of object to be "observed"
    """
    def __init__(self, name):
        self._observers = []
        self.name = name

    def add_observer(self,observer):
        self._observers.append(observer)

    def remove_observer(self,observer):
        self._observers.remove(observer)

    def notify_observer(self,  *obj, **kwargs):
        for observer in self._observers:
            observer.update(self.name, *obj, **kwargs)

class Token(object):
    __slots__ = ["id", "type"]

    def __init__(self, id, type ):
        self.id =  id
        self.type = type
