import sys

from doit.api import run

def test_execute(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['did'])
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
