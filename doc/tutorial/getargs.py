DOIT_CONFIG = {'default_tasks': ['use_cmd', 'use_python']}

def task_compute():
   def comp():
       return {'x':5,'y':10, 'z': 20}
   return {'actions': [(comp,)]}


def task_use_cmd():
   return {'actions': ['echo x=%(x)s, z=%(z)s'],
           'getargs': {'x':'compute.x',
                       'z':'compute.z'},
           'verbosity': 2,
           }


def task_use_python():
  return {'actions': [show_getargs],
          'getargs': {'x':'compute.x',
                      'y':'compute.y'},
          'verbosity': 2,
          }
def show_getargs(x, y):
   print "this is x:%s" % x
   print "this is y:%s" % y
