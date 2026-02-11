import os
import unittest
from unittest import mock
from unittest.mock import patch

from doit import version
from doit.cmdparse import CmdParseError, CmdParse
from doit.exceptions import InvalidCommand, InvalidDodoFile
from doit.dependency import FileChangedChecker, JSONCodec
from doit.task import Task
from doit.loader import task_params
from doit.cmd_base import version_tuple, Command, DoitCmdBase
from doit.cmd_base import get_loader, ModuleTaskLoader, DodoTaskLoader
from doit.cmd_base import check_tasks_exist, tasks_and_deps_iter, subtasks_iter
from tests.support import CmdFactory, RestoreCwdMixin, DepfileNameMixin
from tests.support import DepManagerMixin


class TestVersionTuple(unittest.TestCase):
    def test_version_tuple(self):
        self.assertEqual([1, 2, 3], version_tuple([1, 2, 3]))
        self.assertEqual([1, 2, 3], version_tuple('1.2.3'))
        self.assertEqual([0, 2, 0], version_tuple('0.2.0'))
        self.assertEqual([0, 2, -1], version_tuple('0.2.dev1'))


opt_bool = {'name': 'flag',
            'short': 'f',
            'long': 'flag',
            'inverse': 'no-flag',
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
           'short': 'n',
           'long': 'number',
           'type': int,
           'default': 5,
           'help': 'help for opt3 [default: %(default)s]'}

opt_no = {'name': 'no',
          'short': '',
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


class TestCommand(unittest.TestCase):

    def test_configure(self):
        config = {'GLOBAL': {'foo': 1, 'bar': '2'},
                  'whatever': {'xxx': 'yyy'},
                  'samplecmd': {'foo': 4}}
        cmd = SampleCmd(config=config)
        self.assertEqual(config, cmd.config)
        self.assertEqual({'foo': 4, 'bar': '2'}, cmd.config_vals)

    def test_call_value_cmd_line_arg(self):
        cmd = SampleCmd()
        params, args = cmd.parse_execute(['-n', '7', 'ppp'])
        self.assertEqual(['ppp'], args)
        self.assertEqual(7, params['num'])

    def test_call_value_option_default(self):
        cmd = SampleCmd()
        params, args = cmd.parse_execute([])
        self.assertEqual(5, params['num'])

    def test_call_value_overwritten_default(self):
        cmd = SampleCmd(config={'GLOBAL': {'num': 20}})
        params, args = cmd.parse_execute([])
        self.assertEqual(20, params['num'])

    def test_help(self):
        cmd = SampleCmd(config={'GLOBAL': {'num': 20}})
        text = cmd.help()
        self.assertIn('PURPOSE-X', text)
        self.assertIn('USAGE-X', text)
        self.assertIn('DESCRIPTION-X', text)
        self.assertIn('-f', text)
        self.assertIn('--rare-bool', text)
        self.assertIn('help for opt1', text)
        self.assertIn('my-section', text)
        self.assertIn(opt_no['name'], [o.name for o in cmd.get_options()])
        self.assertIn("DOIT_RARE", text)
        self.assertNotIn('user cant modify me', text)
        self.assertIn("help for opt2 [default: False]", text)
        self.assertIn("help for opt3 [default: 20]", text)

    def test_failCall(self):
        cmd = SampleCmd()
        self.assertRaises(CmdParseError, cmd.parse_execute, ['-x', '35'])


class TestModuleTaskLoader(unittest.TestCase):
    def test_load_tasks_from_dict(self):
        cmd = Command()
        members = {'task_xxx1': lambda: {'actions': []},
                   'task_no': 'strings are not tasks',
                   'blabla': lambda: None,
                   'DOIT_CONFIG': {'verbose': 2}}
        loader = ModuleTaskLoader(members)
        loader.setup({})
        config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        self.assertEqual(['xxx1'], [t.name for t in task_list])
        self.assertEqual({'verbose': 2}, config)

    def test_load_tasks_from_module(self):
        import tests.module_with_tasks as module
        loader = ModuleTaskLoader(module)
        loader.setup({})
        config = loader.load_doit_config()
        task_list = loader.load_tasks(Command(), [])
        self.assertEqual(['xxx1'], [t.name for t in task_list])
        self.assertEqual({'verbose': 2}, config)

    def test_task_opt_from_api_to_creator(self):
        cmd = Command()

        @task_params([{'name': 'x', 'long': 'x', 'default': None}])
        def creator(x):
            return {
                'actions': None,
                'targets': [x],
            }
        members = {'task_foo': creator}
        loader = ModuleTaskLoader(members)
        loader.setup({})
        loader.task_opts = {'foo': {'x': 'dep'}}
        task_list = loader.load_tasks(cmd, [])
        t = task_list.pop()
        self.assertEqual('dep', t.targets[0])

    def test_task_config(self):
        cmd = Command()
        members = {
            'task_foo': lambda: {'actions': [],
                                 'params': [{'name': 'x', 'default': None,
                                             'long': 'x'}]},
            'DOIT_CONFIG': {'task:foo': {'x': 1}},
        }
        loader = ModuleTaskLoader(members)
        loader.setup({})
        loader.config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        t = task_list.pop()
        t.init_options()
        self.assertEqual(1, t.options['x'])

    def test_task_opt_from_api_to_action(self):
        cmd = Command()
        members = {
            'task_foo': lambda: {
                'actions': [],
                'params': [{'name': 'x', 'default': None, 'long': 'x'}]},
        }
        loader = ModuleTaskLoader(members)
        loader.setup({})
        loader.task_opts = {'foo': {'x': 2}}
        task_list = loader.load_tasks(cmd, [])
        t = task_list.pop()
        t.init_options()
        self.assertEqual(2, t.options['x'])


class TestDodoTaskLoader(RestoreCwdMixin, unittest.TestCase):
    def test_load_tasks(self):
        os.chdir(os.path.join(os.path.dirname(__file__), '..', 'tests'))
        cmd = Command()
        params = {'dodoFile': 'loader_sample.py',
                  'cwdPath': None,
                  'seek_file': False}
        loader = DodoTaskLoader()
        loader.setup(params)
        config = loader.load_doit_config()
        task_list = loader.load_tasks(cmd, [])
        self.assertEqual(['xxx1', 'yyy2'], [t.name for t in task_list])
        self.assertEqual({'verbose': 2}, config)


class TestDoitCmdBase(DepfileNameMixin, unittest.TestCase):
    class MyCmd(DoitCmdBase):
        doc_purpose = "fake for testing"
        doc_usage = "[TASK ...]"
        doc_description = None

        opt_my = {
            'name': 'my_opt',
            'short': 'm',
            'long': 'mine',
            'type': str,
            'default': 'xxx',
            'help': "my option"
        }

        cmd_options = (opt_my,)

        def _execute(self, my_opt):
            return my_opt

    def test_new_cmd(self):
        class MyRawCmd(self.MyCmd):
            def execute(self, params, args):
                return params['my_opt']

        members = {'task_xxx1': lambda: {'actions': []}}
        cmds = {'foo': None, 'bar': None}
        loader = get_loader({}, task_loader=ModuleTaskLoader(members), cmds=cmds)
        mycmd = MyRawCmd(task_loader=loader)
        self.assertEqual(['bar', 'foo'], mycmd.loader.cmd_names)
        self.assertEqual('min', mycmd.parse_execute(['--mine', 'min']))

    def test_execute(self):
        members = {'task_xxx1': lambda: {'actions': []}}
        loader = get_loader({}, task_loader=ModuleTaskLoader(members))
        mycmd = self.MyCmd(task_loader=loader)
        self.assertEqual('min', mycmd.parse_execute([
            '--db-file', self.depfile_name, '--mine', 'min']))

    @mock.patch('doit.cmd_base.Globals')
    def test_execute_provides_dep_manager(self, mock_globals):
        mock_globals.dep_manager = None
        members = {'task_xxx1': lambda: {'actions': []}}

        class MockTaskLoader(ModuleTaskLoader):
            def load_tasks(self, cmd, pos_args):
                assert mock_globals.dep_manager
                return super().load_tasks(cmd, pos_args)

        loader = get_loader({}, task_loader=MockTaskLoader(members))
        mycmd = self.MyCmd(task_loader=loader)
        mycmd.parse_execute(['--db-file', self.depfile_name, '--mine', 'min'])
        self.assertEqual(mock_globals.dep_manager, mycmd.dep_manager)

    def test_minversion(self):
        members = {
            'task_xxx1': lambda: {'actions': []},
            'DOIT_CONFIG': {'minversion': '5.2.3'},
        }
        loader = ModuleTaskLoader(members)

        with patch.object(version, 'VERSION', '7.5.8'):
            mycmd = self.MyCmd(task_loader=loader)
            self.assertEqual('xxx', mycmd.parse_execute(
                ['--db-file', self.depfile_name]))

        with patch.object(version, 'VERSION', '5.2.1'):
            mycmd = self.MyCmd(task_loader=loader)
            self.assertRaises(InvalidDodoFile, mycmd.parse_execute, [])

    def testInvalidChecker(self):
        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['check_file_uptodate'] = 'i dont exist'
        self.assertRaises(InvalidCommand, mycmd.execute, params, args)

    def testCustomChecker(self):
        class MyChecker(FileChangedChecker):
            pass

        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['check_file_uptodate'] = MyChecker
        params['dep_file'] = self.depfile_name
        mycmd.execute(params, args)
        self.assertIsInstance(mycmd.dep_manager.checker, MyChecker)

    def testCustomCodec(self):
        class MyCodec(JSONCodec):
            pass

        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}))
        params, args = CmdParse(mycmd.get_options()).parse([])
        params['codec_cls'] = MyCodec
        params['dep_file'] = self.depfile_name
        mycmd.execute(params, args)
        self.assertIsInstance(mycmd.dep_manager.backend.codec, MyCodec)

    def testPluginBackend(self):
        mycmd = self.MyCmd(task_loader=ModuleTaskLoader({}),
                           config={'BACKEND': {'j2': 'doit.dependency:JsonDB'}})
        params, args = CmdParse(mycmd.get_options()).parse(['--backend', 'j2'])
        params['dep_file'] = self.depfile_name
        mycmd.execute(params, args)
        self.assertIs(mycmd._backends['j2'], mycmd.dep_manager.db_class)

    def testPluginLoader(self):
        entry_point = {'mod': 'tests.sample_plugin:MyLoader'}
        config = {
            'GLOBAL': {'loader': 'mod'},
            'LOADER': entry_point,
        }
        loader = get_loader(config)
        mycmd = self.MyCmd(task_loader=loader, config=config)
        self.assertEqual('MyLoader', mycmd.loader.__class__.__name__)
        dodo_config = mycmd.loader.load_doit_config()
        task_list = mycmd.loader.load_tasks(mycmd, [])
        self.assertEqual('sample_task', task_list[0].name)
        self.assertEqual({'verbosity': 2}, dodo_config)


class TestForceVerbosity(DepManagerMixin, unittest.TestCase):
    def test_force_verbosity(self):
        members = {
            'DOIT_CONFIG': {'verbosity': 0},
            'task_xxx1': lambda: {'actions': []},
        }
        loader = ModuleTaskLoader(members)

        class SampleCmd(DoitCmdBase):
            opt_verbosity = {
                'name': 'verbosity',
                'short': 'v',
                'long': 'verbosity',
                'type': int,
                'default': None,
                'help': "verbosity foo"
            }
            cmd_options = (opt_verbosity,)

            def _execute(self, verbosity, force_verbosity):
                return verbosity, force_verbosity

        cmd = CmdFactory(SampleCmd, task_loader=loader,
                         dep_manager=self.dep_manager)
        self.assertEqual((2, True), cmd.parse_execute(
            ['--db-file', self.dep_manager.name, '-v2']))
        self.assertEqual((0, False), cmd.parse_execute(
            ['--db-file', self.dep_manager.name]))


class TestCheckTasksExist(unittest.TestCase):
    def test_None(self):
        check_tasks_exist({}, None)

    def test_invalid(self):
        self.assertRaises(InvalidCommand, check_tasks_exist, {}, 't2')

    def test_valid(self):
        tasks = {
            't1': Task("t1", [""]),
            't2': Task("t2", [""], task_dep=['t1']),
        }
        check_tasks_exist(tasks, ['t2'])


class TestTaskAndDepsIter(unittest.TestCase):

    def test_dep_iter(self):
        tasks = {
            't1': Task("t1", [""]),
            't2': Task("t2", [""], task_dep=['t1']),
            't3': Task("t3", [""], setup=['t1']),
            't4': Task("t4", [""], task_dep=['t3']),
        }
        def names(sel_tasks, repeated=False):
            task_list = tasks_and_deps_iter(tasks, sel_tasks, repeated)
            return [t.name for t in task_list]

        self.assertEqual(['t1'], names(['t1']))
        self.assertEqual(['t2', 't1'], names(['t2']))
        self.assertEqual(['t3', 't1'], names(['t3']))
        self.assertEqual(['t4', 't3', 't1'], names(['t4']))
        self.assertEqual(set(['t2', 't1']), set(names(['t1', 't2'])))
        got = names(['t1', 't2'], True)
        self.assertEqual(3, len(got))
        self.assertEqual('t1', got[-1])


class TestSubtaskIter(unittest.TestCase):

    def test_sub_iter(self):
        tasks = {
            't1': Task("t1", [""]),
            't1:x': Task("t1:x", [""], subtask_of='t1'),
            't2': Task("t2", [""], task_dep=['t1', 't1:x', 't2:a', 't2:b']),
            't2:a': Task("t2:a", [""], subtask_of='t2'),
            't2:b': Task("t2:b", [""], subtask_of='t2'),
        }
        def names(task_name):
            return [t.name for t in subtasks_iter(tasks, tasks[task_name])]

        self.assertEqual([], names('t1'))
        self.assertEqual(['t2:a', 't2:b'], names('t2'))
