"""stuff dealing with incompatibilities between python versions"""
import sys

PY3 = (sys.version_info[0] >= 3)

# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:  # pragma: no cover
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json
json # pyflakes

import inspect
if PY3:
    is_bound_method = inspect.ismethod
else:
    # In Python 2, ismethod() returns True for both bound & unbound methods.
    def is_bound_method(obj):
        return inspect.ismethod(obj) and (getattr(obj, '__self__', None) is not None)
