"""stuff dealing with incompatibilities between python versions"""

import types


# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:  # pragma: no cover
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json
json # pyflakes


# python2.6 added isgenerator
def isgenerator(obj):
    """Check if object type is a generator.

    @param object: object to test.
    @return: (bool) object is a generator?"""
    return type(obj) is types.GeneratorType
