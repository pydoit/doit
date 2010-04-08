DOIT_CONFIG = {'default_tasks': ['use']}

def task_compute():
   def comp():
       return {'x':5,'y':10, 'z': 20}
   return {'actions': [(comp,)]}


def task_use():
   return {'actions': ['echo %(x)s %(z)s - 5 20'],
           'getargs': {'x':'compute.x',
                        'z':'compute.z'},
           'verbosity': 2,
           }
