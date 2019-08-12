import os

from unittest import mock
import pytest

from doit import version
from doit.cmdparse import CmdParseError, CmdParse
from doit.exceptions import InvalidCommand, InvalidDodoFile
from doit.dependency import FileChangedChecker, JSONCodec
from doit.task import Task
from doit.cmd_base import version_tuple, Command, DoitCmdBase, TaskLoader
from doit.cmd_base import get_loader, ModuleTaskLoader, DodoTaskLoader
from doit.cmd_base import check_tasks_exist, tasks_and_deps_iter, subtasks_iter
from .conftest import CmdFactory


def test_version_tuple():
    assert [1,2,3] == version_tuple([1,2,3])
    assert [1,2,3] == version_tuple('1.2.3')
    assert [0,2,0] == version_tuple('0.2.0')
    assert [0,2,-1] == version_tuple('0.2.dev1')


opt_bool = {'name': 'flag',
            'short':'f',
            'long': 'flag',
            'inverse':'no-flag',
            'type': bool,
            'default': False,
            'help': 'help for opt1'}

opt_rare = {'section': 'my-section',
            'name': 'rare',
            'long': 'rare-bool',
            'type': bool,
            'default': False,
            'env_var': 'DOIT_RARE',
            'help': 'help for opt2 [default: %(default)s]'}

opt_int = {'name': 'num',
           'short':'n',
           'long': 'number',
           'type': int,
           'default': 5,
           'help': 'help for opt3 [default: %(default)s]'}

opt_no = {'name': 'no',
          'short':'',
          'long': '',
          'type': int,
          'default': 5,
          'help': 'user cant modify me'}



class SampleCmd(Command):
    doc_purpose = 'PURPOSE-X'
    doc_usage = 'USAGE-X'
    doc_description = 'DESCRIPTION-X'

    cmd_options = [opt_bool, opt_rare, opt_int, opt_no]

    @staticmethod
    def execute(params, args):
        return params, args


class TestCommand(object):

    def test_configure(self):
        config = {'GLOBAL':{'foo':1, 'bar':'2'},
                  'whatever':{'xxx': 'yyy'},
                  'samplecmd': {'foo':4},
        }
        cmd = SampleCmd(config=config)
        assert cmd.config == config
        assert cmd.config_vals == {'foo':4, 'bar':'2'}

    def test_call_value_cmd_line_arg(self):
        cmd = SampleCmd()
        params, args = cmd.parse_execute(['-n','7','ppp'])
        assert ['ppp'] == args
        assert 7 == params['num']

    def test_call_value_option_default(self):
        cmd = SampleCmd()
        params, args = cmd.parse_execute([])
        assert 5 == params['num']

    def test_call_value_overwritten_default(self):
        cmd = SampleCmd(config={'GLOBAL':{'num': 20}})
        params, args = cmd.parse_execute([])
        assert 20 == params['num']

    def test_help(self):
        cmd = SampleCmd(config={'GLOBAL':{'num': 20}})
        text = cmd.help()
        assert 'PURPOSE-X' in text
        assert 'USAGE-X' in text
        assert 'DESCRIPTION-X' in text
        assert '-f' in text
        assert '--rare-bool' in text
        assert 'help for opt1' in text
        assert 'my-section' in text
        assert opt_no['name'] in [o.name for o in cmd.get_options()]
        assert "DOIT_RARE" in text

        # option wihtout short and long are not displayed
        assert 'user cant modify me' not in text

        # default value is displayed
        assert "help for opt2 [default: False]" in text

        # overwritten default
        assert "help for opt3 [default: 20]" in text


    def test_failCall(self):
        cmd = SampleCmd()
        pytest.raises(CmdParseError, cmd.parse_execute, ['-x','35'])



class TestModuleTaskLoader(object):
    def test_load_tasks_from_dict(self):
        cmd = Command()
        members = {'task_xxx1': lambda : {'actions':[]},
                   'task_no': 'strings are not tasks',
                   'blabla': lambda :None,
                   'DOIT_CONFIG': {'verbose': 2},
                   }
        loader = ModuleTaskLoader(members)
        loader.setup({})
        config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        assert ['xxx1'] == [t.name for t in task_list]
        assert {'verbose': 2} == config

    def test_load_tasks_from_module(self):
        import tests.module_with_tasks as module
        loader = ModuleTaskLoader(module)
        loader.setup({})
        config = loader.load_doit_config()
        task_list = loader.load_tasks(Command(), [])
        assert ['xxx1'] == [t.name for t in task_list]
        assert {'verbose': 2} == config

    def test_task_config(self):
        cmd = Command()
        members = {'task_foo': lambda: {'actions':[],
                                        'params': [{
                                            'name': 'x',
                                            'default': None,
                                            'long': 'x'
                                        }]},
                   'DOIT_CONFIG': {'task:foo': {'x': 1}},
                   }
        loader = ModuleTaskLoader(members)
        loader.setup({})
        loader.config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        task = task_list.pop()
        task.init_options()
        assert 1 == task.options['x']

class TestDodoTaskLoader(object):
    def test_load_tasks(self, restore_cwd):
        os.chdir(os.path.dirname(__file__))
        cmd = Command()
        params = {'dodoFile': 'loader_sample.py',
                  'cwdPath': None,
                  'seek_file': False,
                  }
        loader = DodoTaskLoader()
        loader.setup(params)
        config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        assert ['xxx1', 'yyy2'] == [t.name for t in task_list]
        assert {'verbose': 2} == config



class TestDoitCmdBase(object):
    class MyCmd(DoitCmdBase):
        doc_purpose = "fake for testing"
        doc_usage = "[TASK ...]"
        doc_description = None

        opt_my = {
            'name': 'my_opt',
            'short':'m',
            'long': 'mine',
            'type': str,
            'default': 'xxx',
            'help': "my option"
           }

        cmd_options = (opt_my,)

        def _execute(self, my_opt):
            return my_opt

    # command with lower level execute() method
    def test_new_cmd(self):
        class MyRawCmd(self.MyCmd):
            def execute(self, params, args):
                return params['my_opt']

        members = {'task_xxx1': lambda : {'actions':[]},}
        cmds = {'foo':None, 'bar':None}
        loader = get_loader({}, task_loader=ModuleTaskLoader(members),
                            cmds=cmds)
        mycmd = MyRawCmd(task_loader=loader)
        assert mycmd.loader.cmd_names == ['bar', 'foo']
        assert 'min' == mycmd.parse_execute(['--mine', 'min'])

    # command with _execute() method
    def test_execute(self, depfile_name):
        members = {'task_xxx1': lambda : {'actions':[]},}
        loader = get_loader({}, task_loader=ModuleTaskLoader(members))

        mycmd = self.MyCmd(task_loader=loader)
        assert 'min' == mycmd.parse_execute([
            '--db-file', depfile_name,
            '--mine', 'min'])


    @mock.patch('doit.cmd_base.Globals')
    def test_execute_provides_dep_manager(self, mock_globals, depfile_name):
        mock_globals.dep_manager = None
        members = {'task_xxx1': lambda: {'actions': []}}

        class MockTaskLoader(ModuleTaskLoader):
            def load_tasks(self, cmd, pos_args):
                # ensure dep_manager is set before tasks are loaded:
                assert mock_globals.dep_manager
                return super().load_tasks(cmd, pos_args)

        loader = get_loader({}, task_loader=MockTaskLoader(members))
        mycmd = self.MyCmd(task_loader=loader)

        mycmd.parse_execute(['--db-file', depfile_name, '--mine', 'min'])
        assert mock_globals.dep_manager == mycmd.dep_manager


    def test_execute_with_legacy_dict_loader(self, depfile_name):
        members = {'task_xxx1': lambda: {'actions': []}}

        class LegacyLoader(TaskLoader):
            def load_tasks(self, cmd, opt_values, pos_args):
                return super()._load_from(cmd, members, [])

        mycmd = self.MyCmd(task_loader=LegacyLoader())
        assert 'min' == mycmd.parse_execute([
            '--db-file', depfile_name,
            '--mine', 'min',
        ])


    def test_execute_with_legacy_module_loader(self, depfile_name):
        import tests.module_with_tasks as module

        class LegacyLoader(TaskLoader):
            def load_tasks(self, cmd, opt_values, pos_args):
                return super()._load_from(cmd, module, [])

        mycmd = self.MyCmd(task_loader=LegacyLoader())
        assert 'min' == mycmd.parse_execute([
            '--db-file', depfile_name,
            '--mine', 'min',
        ])


    # command with _execute() method
    def test_minversion(self, depfile_name, monkeypatch):
        members = {
            'task_xxx1': lambda : {'actions':[]},
            'DOIT_CONFIG': {'minversion': '5.2.3'},
            }
        loader = ModuleTaskLoader(members)

        # version ok
        monkeypatch.setattr(version, 'VERSION', '7.5.8')
        mycmd = self.MyCmd(task_loader=loader)
        assert 'xxx' == mycmd.parse_execute(['--db-file', depfile_name])

        # version too old
        monkeypatch.setattr(version, 'VERSION', '5.2.1')
        mycmd = self.MyCmd(task_loader=loader)
        pytest.raises(InvalidDodoFile, mycmd.parse_execute, [])


    def testInvalidChecker(self):
        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['check_file_uptodate'] = 'i dont exist'
        pytest.raises(InvalidCommand, mycmd.execute, params, args)


    def testCustomChecker(self, depfile_name):
        class MyChecker(FileChangedChecker):
            pass

        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['check_file_uptodate'] = MyChecker
        params['dep_file'] = depfile_name
        mycmd.execute(params, args)
        assert isinstance(mycmd.dep_manager.checker, MyChecker)

    def testCustomCodec(self, depfile_name):
        class MyCodec(JSONCodec):
            pass

        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['codec_cls'] = MyCodec
        params['dep_file'] = depfile_name
        mycmd.execute(params, args)
        assert isinstance(mycmd.dep_manager.backend.codec, MyCodec)


    def testPluginBackend(self, depfile_name):
        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}),
                           config={'BACKEND': {'j2': 'doit.dependency:JsonDB'}})
        params, args = CmdParse(mycmd.get_options()).parse(['--backend', 'j2'])
        params['dep_file'] = depfile_name
        mycmd.execute(params, args)
        assert mycmd.dep_manager.db_class is mycmd._backends['j2']


    def testPluginLoader(self):
        entry_point = {'mod': 'tests.sample_plugin:MyLoader'}
        config = {
            'GLOBAL': {'loader': 'mod'},
            'LOADER': entry_point,
        }
        loader = get_loader(config)
        mycmd = self.MyCmd(task_loader=loader, config=config)
        assert mycmd.loader.__class__.__name__ == 'MyLoader'
        task_list, dodo_config = mycmd.loader.load_tasks(mycmd, {}, [])
        assert task_list[0].name == 'sample_task'
        assert dodo_config == {'verbosity': 2}


    def test_force_verbosity(self, dep_manager):
        members = {
            'DOIT_CONFIG': {'verbosity': 0},
            'task_xxx1': lambda : {'actions':[]},
        }
        loader = ModuleTaskLoader(members)

        class SampleCmd(DoitCmdBase):
            opt_verbosity = {
                'name':'verbosity',
                'short':'v',
                'long':'verbosity',
                'type':int,
                'default': None,
                'help': "verbosity foo"
            }
            cmd_options = (opt_verbosity, )

            def _execute(self, verbosity, force_verbosity):
                return verbosity, force_verbosity

        cmd = CmdFactory(SampleCmd, task_loader=loader, dep_manager=dep_manager)
        assert (2, True) == cmd.parse_execute(
            ['--db-file', dep_manager.name, '-v2'])
        assert (0, False) == cmd.parse_execute(['--db-file', dep_manager.name])



class TestCheckTasksExist(object):
    def test_None(self):
        check_tasks_exist({}, None)
        # nothing is raised

    def test_invalid(self):
        pytest.raises(InvalidCommand, check_tasks_exist, {}, 't2')

    def test_valid(self):
        tasks = {
            't1': Task("t1", [""] ),
            't2': Task("t2", [""], task_dep=['t1']),
            }
        check_tasks_exist(tasks, ['t2'])
        # nothing is raised


class TestTaskAndDepsIter(object):

    def test_dep_iter(self):
        tasks = {
            't1': Task("t1", [""] ),
            't2': Task("t2", [""], task_dep=['t1']),
            't3': Task("t3", [""], setup=['t1']),
            't4': Task("t4", [""], task_dep=['t3']),
            }
        def names(sel_tasks, repeated=False):
            task_list = tasks_and_deps_iter(tasks, sel_tasks, repeated)
            return [t.name for t in task_list]

        # no deps
        assert ['t1'] == names(['t1'])
        # with task_dep
        assert ['t2', 't1'] == names(['t2'])
        # with setup
        assert ['t3', 't1'] == names(['t3'])
        # two levels
        assert ['t4', 't3', 't1'] == names(['t4'])
        # select 2
        assert set(['t2', 't1']) == set(names(['t1', 't2']))
        # repeat deps
        got = names(['t1', 't2'], True)
        assert 3 == len(got)
        assert 't1' == got[-1]


class TestSubtaskIter(object):

    def test_sub_iter(self):
        tasks = {
            't1': Task("t1", [""] ),
            't1:x': Task("t1:x", [""], subtask_of='t1'),
            't2': Task("t2", [""], task_dep=['t1', 't1:x', 't2:a', 't2:b']),
            't2:a': Task("t2:a", [""], subtask_of='t2'),
            't2:b': Task("t2:b", [""], subtask_of='t2'),
            }
        def names(task_name):
            return [t.name for t in subtasks_iter(tasks, tasks[task_name])]

        assert [] == names('t1')
        assert ['t2:a', 't2:b'] == names('t2')
