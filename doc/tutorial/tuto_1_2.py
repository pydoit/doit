import pathlib
import pygraphviz

from import_deps import PyModule, ModuleSet

def get_imports(module_path):
    module = PyModule(module_path)
    base_path = module.pkg_path().resolve()
    mset = ModuleSet(base_path.glob('**/*.py'))
    imports = mset.get_imports(module, return_fqn=True)
    return {'modules': list(sorted(imports))}

def task_imports():
    """find imports from a python module"""
    module_path = 'projects/requests/requests/models.py'
    return {
        'file_dep': [module_path],
        'actions': [(get_imports, [module_path])],
    }


def module_to_dot(source, sinks, targets):
    graph = pygraphviz.AGraph(strict=False, directed=True)
    graph.node_attr['color'] = 'lightblue2'
    graph.node_attr['style'] = 'filled'
    for sink in sinks:
        graph.add_edge(source, sink)
    graph.write(targets[0])


def task_dot():
    """generate a graphviz's dot graph from module imports"""
    return {
        'targets': ['requests.models.dot'],
        'actions': [(module_to_dot, (), {'source': 'requests.models'})],
        'getargs': {'sinks': ('imports', 'modules')},
        'clean': True,
    }


def task_draw():
    """generate image from a dot file"""
    return {
        'file_dep': ['requests.models.dot'],
        'targets': ['requests.models.png'],
        'actions': ['dot -Tpng %(dependencies)s -o %(targets)s'],
        'clean': True,
    }
