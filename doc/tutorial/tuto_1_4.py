import pathlib
import pygraphviz

from import_deps import PyModule, ModuleSet


DOIT_CONFIG = {
    'default_tasks': ['imports', 'dot', 'draw'],
}


base_path = pathlib.Path('projects/requests/requests')
PKG_MODULES = ModuleSet(base_path.glob('**/*.py'))


def get_imports(pkg_modules, module_path):
    module = pkg_modules.by_path[module_path]
    imports = pkg_modules.get_imports(module, return_fqn=True)
    return {'modules': list(sorted(imports))}


def task_imports():
    """find imports from a python module"""
    for name, module in PKG_MODULES.by_name.items():
        yield {
            'name': name,
            'file_dep': [module.path],
            'actions': [(get_imports, (PKG_MODULES, module.path))],
        }


def print_imports(modules):
    print('\n'.join(modules))

def task_print():
    """print on stdout list of direct module imports"""
    for name, module in PKG_MODULES.by_name.items():
        yield {
            'name': name,
            'actions': [print_imports],
            'getargs': {'modules': ('imports:{}'.format(name), 'modules')},
            'uptodate': [False],
            'verbosity': 2,
        }


def module_to_dot(imports, targets):
    graph = pygraphviz.AGraph(strict=False, directed=True)
    graph.node_attr['color'] = 'lightblue2'
    graph.node_attr['style'] = 'filled'
    for source, sinks in imports.items():
        for sink in sinks:
            graph.add_edge(source, sink)
    graph.write(targets[0])

def task_dot():
    """generate a graphviz's dot graph from module imports"""
    return {
        'targets': ['requests.dot'],
        'actions': [module_to_dot],
        'getargs': {'imports': ('imports', 'modules')},
        'clean': True,
    }


def task_draw():
    """generate image from a dot file"""
    return {
        'file_dep': ['requests.dot'],
        'targets': ['requests.png'],
        'actions': ['dot -Tpng %(dependencies)s -o %(targets)s'],
        'clean': True,
    }
