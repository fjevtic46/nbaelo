import collections
import functools

from datetime import datetime

import pytz


def now_pst():
    now = datetime.utcnow()
    return pytz.utc.localize(now).astimezone(pytz.timezone('US/Pacific'))


class Memoized:
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    Snippet taken from:
        https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)


memoized = Memoized


class MemoizedTtl(object):
    """Decorator that caches a function's return value each time it is called within a TTL
    If called within the TTL and the same arguments, the cached value is returned,
    If called outside the TTL or a different value, a fresh value is returned.
    http://jonebird.com/2012/02/07/python-memoize-decorator-with-ttl-argument/
    """

    def __init__(self, ttl):
        self.cache = {}
        self.ttl = ttl

    def __call__(self, f):
        def wrapped_f(*args):
            now = time.time()
            try:
                value, last_update = self.cache[args]
                if self.ttl > 0 and now - last_update > self.ttl:
                    raise AttributeError
                #print 'DEBUG: cached value'
                return value
            except (KeyError, AttributeError):
                value = f(*args)
                self.cache[args] = (value, now)
                #print 'DEBUG: fresh value'
                return value
            except TypeError:
                # uncachable -- for instance, passing a list as an argument.
                # Better to not cache than to blow up entirely.
                return f(*args)
        return wrapped_f


memoized_ttl = MemoizedTtl