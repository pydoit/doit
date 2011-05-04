import os

import py

from doit.dependency import Dependency


TESTDB = os.path.join(os.path.dirname(__file__), "testdb")


def remove_db(filename):
    """remove db file from anydbm"""
    extensions = ['', #dbhash #gdbm
                  '.bak', #dumbdb
                  '.dat', #dumbdb
                  '.dir', #dumbdb #dbm
                  '.db', #dbm
                  '.pag', #dbm
                  ]
    for ext in extensions:
        if os.path.exists(filename + ext):
            os.remove(filename + ext)


# fixture for "doit.db". create/remove for every test
def pytest_funcarg__depfile(request):
    def create_depfile():
        if hasattr(request, 'param'):
            dep_class = request.param
        else:
            dep_class = Dependency

        # copied from tempdir plugin
        name = request._pyfuncitem.name
        name = py.std.re.sub("[\W]", "_", name)
        my_tmpdir = request.config._tmpdirhandler.mktemp(name, numbered=True)
        return dep_class(os.path.join(my_tmpdir.strpath, "testdb"))
        # do not use tempfile use TESTDB
        # return dep_class(TESTDB)

    def remove_depfile(depfile):
        if not depfile._closed:
            depfile.close()
        remove_db(depfile.name)

    return request.cached_setup(
        setup=create_depfile,
        teardown=remove_depfile,
        scope="function")


def pytest_funcarg__cwd(request):
    """set cwd to parent folder of this file."""
    def set_cwd():
        cwd = {}
        cwd['previous'] = os.getcwd()
        cwd['current'] = os.path.abspath(os.path.dirname(__file__))
        os.chdir(cwd['current'])
        return cwd
    def restore_cwd(cwd):
        os.chdir(cwd['previous'])
    return request.cached_setup(
        setup=set_cwd,
        teardown=restore_cwd,
        scope="function")
