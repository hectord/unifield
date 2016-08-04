
import inspect
from lru import LRU
import time

config = {}
config['cache_timeout'] = 2000

def is_hashable(h):
    try:
        hash(h)
        return True
    except TypeError:
        return False

def _generate_keys(multi, dbname, kwargs2, reset_fields=[]):
    """
    Generate keys depending of the arguments and the mutli value
    """

    def to_tuple(d):
        pairs = d.items()
        pairs.sort(key=lambda (k,v): k)
        for i, (k, v) in enumerate(pairs):
            if isinstance(v, dict):
                pairs[i] = (k, to_tuple(v))
            if isinstance(v, (list, set)):
                pairs[i] = (k, tuple(v))
            elif not is_hashable(v):
                pairs[i] = (k, repr(v))
        return tuple(pairs)

    if not multi:
        key = (('dbname', dbname),) + to_tuple(kwargs2)
        yield key, None
    else:
        multis = kwargs2[multi][:]
        for id in multis:
            kwargs2[multi] = (id,)
            for reset_field in reset_fields:
                kwargs2[reset_field] = None
            key = (('dbname', dbname),) + to_tuple(kwargs2)
            yield key, id

class read_cache(object):
    """
    Use it as a decorator of the function you plan to cache
    Timeout: 0 = no timeout, otherwise in seconds
    """

    def __init__(self, prefetch=[], context=[], timeout=None, size=8192):
        if timeout is None:
            self.timeout = config['cache_timeout']
        else:
            self.timeout = timeout
        self.lasttime = time.time()
        self.cache = LRU(size)
        self.fun = None
        self._context = context

    def _unify_args(self, *args, **kwargs):
        # Update named arguments with positional argument values (without self and cr)
        kwargs2 = self.fun_default_values.copy()
        kwargs2.update(kwargs)
        kwargs2.update(dict(zip(self.fun_arg_names, args)))
        return kwargs2

    def __call__(self, fn):
        if self.fun is not None:
            raise Exception("Can not use a cache instance on more than one function")
        self.fun = fn

        argspec = inspect.getargspec(fn)
        # get rid of self and the database cursor
        self.fun_arg_names = argspec[0][2:]
        self.fun_default_values = {}
        if argspec[3]:
            self.fun_default_values = dict(zip(self.fun_arg_names[-len(argspec[3]):], argspec[3]))

        def cached_result(self2, cr, *args, **kwargs):
            import time
            if time.time()-int(self.timeout) > self.lasttime:
                self.lasttime = time.time()
                t = time.time()-int(self.timeout)
                old_keys = [key for key in self.cache.keys() if self.cache[key][1] < t]
                for key in old_keys:
                    print "POP", key
                    self.cache.pop(key)

            kwargs2 = self._unify_args(*args, **kwargs)

            # we have to remove from the context what doesn't impact the results
            simplified_context = dict(filter(lambda (key, value) : key in self._context, kwargs2['context'].iteritems()))
            kwargs2['context'] = simplified_context

            # we have to keep in mind the fields that have to be returned
            #  they will be erased when generating the key in the cache
            fields_to_read = kwargs2['fields_to_read']

            result = []
            notincache = {}
            for key, id in _generate_keys('ids', cr.dbname, kwargs2, ['fields_to_read']):
                if key in self.cache:
                    # we have to find if we have all the required fields in the cache
                    values = self.cache[key][0]

                    fields_already_in_the_cache = values.keys()

                    if set(fields_to_read).issubset(set(fields_already_in_the_cache)):
                        # all the values are already in the cache, we don't
                        #  have to ask the DB for more information
                        row = {'id': id}
                        for field in fields_to_read:
                            row[field] = values[field]
                        result.append(row)
                    else:
                        # we have to look for the new values
                        #  we fetch all of them (not optimal since some fields
                        #  could already exist)
                        notincache[id] = key
                else:
                    notincache[id] = key

            if notincache:
                kwargs2['ids'] = notincache.keys()
                kwargs2['fields_to_read'] = fields_to_read

                result2 = fn(self2, cr, **kwargs2)

                # we have to add the new rows in the resultset
                for id, value in map(lambda x : (x['id'], x), result2):
                    key = notincache[id]
                    if key in self.cache:
                        value_in_cache, t = self.cache[key]
                    else:
                        value_in_cache, t = {}, time.time()

                    for field in kwargs2['fields_to_read']:
                        value_in_cache[field] = value[field]
                    value_in_cache['id'] = id

                    self.cache[key] = (value_in_cache, t)

                    result.append(value)

            # TODO: Sort the results according to the sorted row
            return result

        return cached_result


class MyObject(object):

    @read_cache(prefetch=['a', 'c'], context=['context'], timeout=8000, size=3)
    def _read_flat(self, cr, user, ids, fields_to_read, context=None, load='_classic_read'):
        ret = []
        for id in ids:
            row = {'id': id}
            for field in fields_to_read:
                row.update(**{field: id+1})
            ret.append(row)
        return ret

o = MyObject()

class Cursor(object):
    pass
c = Cursor()
c.dbname = 'OK'

print "A"
o._read_flat(c, 1, [1,2,3], ['a'], {'context': 4})
print "B"
#o._read_flat(c, 1, [2], ['b'], {'context': 4})
o._read_flat(c, 1, [1,2], ['c'], {'context': 4})
o._read_flat(c, 1, [3], ['c'], {'context': 4})
print "C"
o._read_flat(c, 1, [1,2,3], ['a', 'c'], {'context': 4})
print "D"

