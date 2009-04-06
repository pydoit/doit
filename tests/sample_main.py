
def task_string():
    return "python sample_process.py sss"

def do_nothing():
    return True

def task_python():
    return do_nothing


def task_dictionary():
    return {'action':'python sample_process.py ddd',
            'targets':['test_runner.py']}

def task_dependency():
    return {'action':do_nothing,
            'dependencies':['test_main.py']}

files = ['test_runner.py','test_util.py']
def task_generator():
    for f in files:
        yield {'action': "python sample_process.py %s"%f,
               'name': f}
    

def funcX(par1,par2,par3):
    if par1 == par2 and par3 > 10:
        return True
           
def task_func_args():
    return {'action':funcX, 
            'kwargs':{'par1':3,'par2':3,'par3':20}}

def task_taskdependency():
    return {'action':do_nothing,
            'dependencies':[":generator"]}

def task_targetdependency():
    return {'action':do_nothing,
            'dependencies':['test_runner.py']}

def task_mygroup():
    return {'action':None,
           'dependencies':[':dictionary',':string']}

