import os

import nose

from doit.task import InvalidTask, BaseTask

class TestDependencyErrorMessages():
    # dependency must be a sequence. give proper error message when anything 
    # else is used.
    def test_dependency_not_sequence(self):
        filePath = os.path.abspath(__file__+"/../"+"data/dependency1")
        ff = open(filePath,"w")
        ff.write("part1")
        ff.close()
        nose.tools.assert_raises(InvalidTask,BaseTask,
                                 "Task X","taskcmd",dependencies=filePath)
