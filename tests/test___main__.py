import subprocess

def test_execute():
    assert 0 == subprocess.call(['python', '-m', 'doit', 'list'])

