import subprocess
from sys import executable


def test_execute(depfile_name):
    assert 0 == subprocess.call([executable, '-m', 'doit', 'list',
                                 '--db-file', depfile_name])
