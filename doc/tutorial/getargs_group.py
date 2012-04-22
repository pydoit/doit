def task_compute():
   def comp(x):
       return {'x':x}
   yield {'name': '5',
          'actions': [ (comp, [5]) ]
          }
   yield {'name': '7',
          'actions': [ (comp, [7]) ]
          }


def show_getargs(values):
    print values
    assert sum(v['x'] for v in values) == 12

def task_args_dict():
  return {'actions': [show_getargs],
          'getargs': {'values': ('compute', None)},
          'verbosity': 2,
          }
