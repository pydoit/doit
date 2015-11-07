"""stuff dealing with incompatibilities between python versions"""


def get_platform_system():
    """return platform.system
    platform module has many regexp, so importing it is slow...
    import only if required
    """
    import platform
    return platform.system()
