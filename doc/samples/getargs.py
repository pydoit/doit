DOIT_CONFIG = {
   'default_tasks': ['use_cmd', 'use_python'],
   'action_string_formatting': 'both',
}

def task_compute():
   def comp():
       return {'x':5,'y':10, 'z': 20}
   return {'actions': [(comp,)]}


def task_use_cmd():
   return {'actions': ['echo x={x}',    # new-style formatting
                       'echo z=%(z)s'], # old-style formatting
           'getargs': {'x': ('compute', 'x'),
                       'z': ('compute', 'z')},
           'verbosity': 2,
           }


def task_use_python():
  return {'actions': [show_getargs],
          'getargs': {'x': ('compute', 'x'),
                      'y': ('compute', 'z')},
          'verbosity': 2,
          }
def show_getargs(x, y):
   print("this is x: {}".format(x))
   print("this is y: {}".format(y))
