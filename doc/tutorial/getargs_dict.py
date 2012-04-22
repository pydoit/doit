def task_compute():
   def comp():
       return {'x':5,'y':10, 'z': 20}
   return {'actions': [(comp,)]}


def show_getargs(values):
   print values

def task_args_dict():
  return {'actions': [show_getargs],
          'getargs': {'values': ('compute', None)},
          'verbosity': 2,
          }
