import pathlib
import pygraphviz


def task_imports():
    """find imports from a python module"""
    return {
        'file_dep': ['projects/requests/requests/models.py'],
        'targets': ['requests.models.deps'],
        'actions': ['python -m import_deps %(dependencies)s > %(targets)s'],
        'clean': True,
    }

def module_to_dot(dependencies, targets):
    graph = pygraphviz.AGraph(strict=False, directed=True)
    graph.node_attr['color'] = 'lightblue2'
    graph.node_attr['style'] = 'filled'
    for dep in dependencies:
        filepath = pathlib.Path(dep)
        source = filepath.stem
        with filepath.open() as fh:
            for line in fh:
                sink = line.strip()
                if sink:
                    graph.add_edge(source, sink)
    graph.write(targets[0])

def task_dot():
    """generate a graphviz's dot graph from module imports"""
    return {
        'file_dep': ['requests.models.deps'],
        'targets': ['requests.models.dot'],
        'actions': [module_to_dot],
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
