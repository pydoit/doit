import subprocess

def test_execute(depfile_name):
    assert 0 == subprocess.call(['python', '-m', 'doit', 'list',
                                 '--db-file', depfile_name])
