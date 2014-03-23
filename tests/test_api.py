import sys

from doit.api import run


def test_execute(monkeypatch, depfile_name):
    monkeypatch.setattr(sys, 'argv', ['did', '--db-file', depfile_name])
    try:
        def hi():
            print('hi')
        def task_hi():
            return {'actions': [hi]}
        run(locals())
    except SystemExit as err:
        assert err.code == 0
    else: # pragma: no cover
        assert False
