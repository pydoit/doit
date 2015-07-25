"""stuff dealing with incompatibilities between python versions"""

import sys
import inspect

PY3 = (sys.version_info[0] >= 3)

# compat for inspect.ismethod
if PY3: # pragma: no cover
    is_bound_method = inspect.ismethod
else:
    # In Python 2, ismethod() returns True for both bound & unbound methods.
    def is_bound_method(obj):
        return (inspect.ismethod(obj) and
                (getattr(obj, '__self__', None) is not None))


def get_platform_system():
    """return platform.system
    platform module has many regexp, so importing it is slow...
    import only if required
    """
    import platform
    return platform.system()
