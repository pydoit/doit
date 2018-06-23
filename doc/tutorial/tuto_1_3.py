import pathlib
import pygraphviz

from import_deps import PyModule, ModuleSet



def get_imports(pkg_modules, module_path):
    module = pkg_modules.by_path[module_path]
    imports = pkg_modules.get_imports(module, return_fqn=True)
    return {'modules': list(sorted(imports))}

def task_imports():
    """find imports from a python module"""
    base_path = pathlib.Path('projects/requests/requests')
    pkg_modules = ModuleSet(base_path.glob('**/*.py'))
    for name, module in pkg_modules.by_name.items():
        yield {
            'name': name,
            'file_dep': [module.path],
            'actions': [(get_imports, (pkg_modules, module.path))],
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
