"""stuff dealing with incompatibilities between python versions"""

# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:  # pragma: no cover
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json
json # pyflakes
