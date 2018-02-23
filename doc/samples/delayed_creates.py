import sys

from doit import create_after

def say_hello(your_name):
    sys.stderr.write("Hello from {}!\n".format(your_name))

def task_a():
    return {
        "actions": [ (say_hello, ["a"]) ]
    }

@create_after("a", creates=['b'])
def task_another_task():
    return {
        "basename": "b",
        "actions": [ (say_hello, ["b"]) ],
    }
