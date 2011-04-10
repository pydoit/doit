DOIT_CONFIG = {'verbosity': 2}

MOD_IMPORTS = {'a': ['b','c'],
               'b': ['f','g'],
               'c': [],
               'f': ['a'],
               'g': []}


def print_deps(mod, dependencies):
    print "%s -> %s" % (mod, dependencies)
def task_mod_deps():
    """task that depends on all direct imports"""
    for mod in MOD_IMPORTS.iterkeys():
        yield {'name': mod,
               'actions': [(print_deps,(mod,))],
               'uptodate': [False],
               'file_dep': [mod],
               'calc_dep': ["get_dep:%s" % mod],
               }

def get_dep(mod):
    # fake implementation
    return {'file_dep': MOD_IMPORTS[mod]}
def task_get_dep():
    """get direct dependencies for each module"""
    for mod in MOD_IMPORTS.iterkeys():
        yield {'name': mod,
               'actions':[(get_dep,[mod])],
               'file_dep': [mod],
               }
