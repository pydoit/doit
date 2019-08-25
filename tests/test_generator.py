from doit.cmd_base import TaskGenerator


class Runner(TaskGenerator):

    @TaskGenerator.doit_task
    def work(self):
        return {
            'actions': None,
        }


class TestGenerator(object):
    def test_tasks(self):
        runner = Runner()
        tasks = runner.doit_tasks()
        assert 'task_work' in tasks
        assert runner.work() == {'actions', None}
