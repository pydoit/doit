import unittest
from io import StringIO

from doit.exceptions import InvalidCommand
from doit.cmdparse import CmdOption
from doit.plugin import PluginDict
from doit.task import Task
from doit.cmd_base import Command, DodoTaskLoader, TaskLoader2
from doit.cmd_completion import TabCompletion
from doit.cmd_help import Help
from tests.support import CmdFactory

# doesnt test the shell scripts. just test its creation!


class FakeLoader2(TaskLoader2):
    def load_doit_config(self):
        return {}

    def load_tasks(self, cmd, pos_args):
        task_list = [
            Task("t1", None),
            Task("t2", None, task_dep=['t2:a'], has_subtask=True),
            Task("t2:a", None, subtask_of='t2'),
        ]
        return task_list


def _make_commands():
    sub_cmds = {}
    sub_cmds['tabcompletion'] = TabCompletion
    sub_cmds['help'] = Help
    return PluginDict(sub_cmds)


class TestInvalidShell(unittest.TestCase):
    def test_invalid_shell_option(self):
        cmd = CmdFactory(TabCompletion)
        self.assertRaises(InvalidCommand, cmd.execute,
                          {'shell':'another_shell', 'hardcode_tasks': False}, [])


class TestCmdCompletionBash(unittest.TestCase):

    def test_with_dodo__dynamic_tasks(self):
        commands = _make_commands()
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=DodoTaskLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        self.assertIn('dodof', got)
        self.assertNotIn('t1', got)
        self.assertIn('tabcompletion', got)

    def test_no_dodo__hardcoded_tasks(self):
        for loader_class in [FakeLoader2]:
            with self.subTest(loader=loader_class.__name__):
                commands = _make_commands()
                output = StringIO()
                cmd = CmdFactory(TabCompletion, task_loader=loader_class(),
                                 outstream=output, cmds=commands)
                cmd.execute({'shell':'bash', 'hardcode_tasks': True}, [])
                got = output.getvalue()
                self.assertNotIn('dodo.py', got)
                self.assertIn('t1', got)

    def test_cmd_takes_file_args(self):
        commands = _make_commands()
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=FakeLoader2(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'bash', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        self.assertIn("""help)
            COMPREPLY=( $(compgen -W "${tasks} ${sub_cmds}" -- $cur) )
            return 0""", got)
        self.assertIn("""tabcompletion)
            COMPREPLY=( $(compgen -f -- $cur) )
            return 0""", got)


class TestCmdCompletionZsh(unittest.TestCase):

    def test_zsh_arg_line(self):
        opt1 = CmdOption({'name':'o1', 'default':'', 'help':'my desc'})
        self.assertEqual('', TabCompletion._zsh_arg_line(opt1))

        opt2 = CmdOption({'name':'o2', 'default':'', 'help':'my desc',
                          'short':'s'})
        self.assertEqual('"-s[my desc]" \\', TabCompletion._zsh_arg_line(opt2))

        opt3 = CmdOption({'name':'o3', 'default':'', 'help':'my desc',
                          'long':'lll'})
        self.assertEqual('"--lll[my desc]" \\', TabCompletion._zsh_arg_line(opt3))

        opt4 = CmdOption({'name':'o4', 'default':'', 'help':'my desc [b]a',
                          'short':'s', 'long':'lll'})
        self.assertEqual('"(-s|--lll)"{-s,--lll}"[my desc [b\\]a]" \\',
                         TabCompletion._zsh_arg_line(opt4))

        # escaping `"` test
        opt5 = CmdOption({'name':'o5', 'default':'',
                          'help':'''my "des'c [b]a''',
                          'short':'s', 'long':'lll'})
        self.assertEqual('''"(-s|--lll)"{-s,--lll}"[my \\"des'c [b\\]a]" \\''',
                         TabCompletion._zsh_arg_line(opt5))

    def test_cmd_arg_list(self):
        no_args = TabCompletion._zsh_arg_list(Command())
        self.assertNotIn("'*::task:(($tasks))'", no_args)
        self.assertNotIn("'::cmd:(($commands))'", no_args)

        class CmdTakeTasks(Command):
            doc_usage = '[TASK ...]'
        with_task_args = TabCompletion._zsh_arg_list(CmdTakeTasks())
        self.assertIn("'*::task:(($tasks))'", with_task_args)
        self.assertNotIn("'::cmd:(($commands))'", with_task_args)

        class CmdTakeCommands(Command):
            doc_usage = '[COMMAND ...]'
        with_cmd_args = TabCompletion._zsh_arg_list(CmdTakeCommands())
        self.assertNotIn("'*::task:(($tasks))'", with_cmd_args)
        self.assertIn("'::cmd:(($commands))'", with_cmd_args)

    def test_cmds_with_params(self):
        commands = _make_commands()
        output = StringIO()
        cmd = CmdFactory(TabCompletion, task_loader=DodoTaskLoader(),
                         outstream=output, cmds=commands)
        cmd.execute({'shell':'zsh', 'hardcode_tasks': False}, [])
        got = output.getvalue()
        self.assertIn("tabcompletion: generate script", got)

    def test_hardcoded_tasks(self):
        for loader_class in [FakeLoader2]:
            with self.subTest(loader=loader_class.__name__):
                commands = _make_commands()
                output = StringIO()
                cmd = CmdFactory(TabCompletion, task_loader=loader_class(),
                                 outstream=output, cmds=commands)
                cmd.execute({'shell':'zsh', 'hardcode_tasks': True}, [])
                got = output.getvalue()
                self.assertIn('t1', got)
