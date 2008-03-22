import os
import sys
import inspect

#TODO do i really need this?
class _TaskGenerator(object):
    """
    An instance of this class is a python function that return tasks
    @ivar name {string}: function name
    @ivar ref {function}: function reference
    @ivar line {integer}: line number of the function on the source code
    """
    def __init__(self,name,ref,line):
        self.name = name
        self.ref = ref
        self.line = line


class Loader(object):
    """load tasks from a python module"""
    taskString = "task_"

    def __init__(self,fileName):
        """@param fileName string path from cwd to module"""

        self.dir_,file_ = os.path.split(os.path.abspath(fileName))
        # make sure dir is on sys.path so we can import it
        sys.path.insert(0,self.dir_)
        # get module containing the tasks
        self.module = __import__(os.path.splitext(file_)[0])

    def getTaskGenerators(self):
        """@return list of _TaskGenerator's define in the target module"""
        # a task generator function name starts with the string self.taskString
        funcs = []
        # get all functions defined in the module
        for name,ref in inspect.getmembers(self.module,inspect.isfunction):
            # ignore functions that are not a task (by its name)
            if not name.startswith(self.taskString):
                continue
            # get line number where function is defined
            line = inspect.getsourcelines(ref)[1]
            # add to list task generator functions
            # remove "task_" from name
            funcs.append(_TaskGenerator(name[5:],ref,line))
        # sort by the order functions were defined (line number)
        funcs.sort(key=lambda obj:obj.line)
        return funcs



    
