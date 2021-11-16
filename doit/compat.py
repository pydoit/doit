"""stuff dealing with incompatibilities between python versions"""

try:
    from multiprocess import Process, Queue as MQueue
    HAS_MULTIPROCESS = True
except ImportError:
    from multiprocessing import Process, Queue as MQueue
    HAS_MULTIPROCESS = False
Process # pyflakes
MQueue # pyflakes


def is_multiprocessing_available():
    # see: http://bugs.python.org/issue3770
    # not available on BSD systens
    try:
        if HAS_MULTIPROCESS:
            import multiprocess.synchronize
            multiprocess
        else:
            import multiprocessing.synchronize
            multiprocessing
    except ImportError: # pragma: no cover
        return False
    else:
        return True


def get_platform_system():
    """return platform.system
    platform module has many regexp, so importing it is slow...
    import only if required
    """
    import platform
    return platform.system()
