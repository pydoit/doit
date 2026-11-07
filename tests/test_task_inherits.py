import io
import os
import shutil
import tempfile
import unittest
import contextlib

from doit.cmd_base import ModuleTaskLoader
from doit.control import TaskControl
from doit.doit_cmd import DoitMain
from doit.exceptions import InvalidDodoFile
from doit.loader import create_after, task_params
from doit.task import Task, InvalidTask
from doit.tools import config_changed


class InheritsTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix='doit-inherits-')
        self.depfile = os.path.join(self.workdir, 'inherits.db')
        self.log = []

    def tearDown(self):
        shutil.rmtree(self.workdir, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.workdir, name)

    def write(self, name, content):
        with open(self.path(name), 'w') as fh:
            fh.write(content)

    def rec(self, label):
        def action():
            self.log.append(label)
        return action

    def doit(self, namespace, *args):
        out = io.StringIO()
        main = DoitMain(
            ModuleTaskLoader(namespace),
            extra_config={'GLOBAL': {'dep_file': self.depfile,
                                     'backend': 'json'}})
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = main.run(list(args))
        return code, out.getvalue()

    def info_block(self, namespace, task_name, field):
        code, out = self.doit(namespace, 'info', '--no-status', task_name)
        self.assertEqual(0, code)
        lines = out.splitlines()
        start = [i for i, line in enumerate(lines)
                 if line.split(':', 1)[0].strip() == field]
        if not start:
            return []
        values = []
        for line in lines[start[0] + 1:]:
            if not line.startswith(' - '):
                break
            values.append(line[3:].strip())
        return values

    def info_line(self, namespace, task_name, field):
        code, out = self.doit(namespace, 'info', '--no-status', task_name)
        self.assertEqual(0, code)
        for line in out.splitlines():
            if line.split(':', 1)[0].strip() == field:
                return line.split(':', 1)[1].strip()
        return None

    def list_doc(self, namespace, task_name):
        code, out = self.doit(namespace, 'list')
        self.assertEqual(0, code)
        for line in out.splitlines():
            parts = line.split(None, 1)
            if parts and parts[0] == task_name:
                return parts[1].strip() if len(parts) > 1 else ''
        self.fail('task %s not listed' % task_name)


class TestInheritDependencies(InheritsTestCase):

    def test_task_dep_own_entries_then_parents_in_order(self):
        ns = {
            'task_a': lambda: {'actions': [self.rec('a')]},
            'task_b': lambda: {'actions': [self.rec('b')]},
            'task_c': lambda: {'actions': [self.rec('c')]},
            'task_p1': lambda: {'actions': [self.rec('p1')],
                                'task_dep': ['b']},
            'task_p2': lambda: {'actions': [self.rec('p2')],
                                'task_dep': ['c']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'task_dep': ['a'],
                                 'inherits': ['p1', 'p2']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['a', 'b', 'c', 'kid'], self.log)
        self.assertEqual(['a', 'b', 'c'], self.info_block(ns, 'kid', 'task_dep'))

    def test_parent_order_decides_task_dep_order(self):
        ns = {
            'task_b': lambda: {'actions': [self.rec('b')]},
            'task_c': lambda: {'actions': [self.rec('c')]},
            'task_p1': lambda: {'actions': None, 'task_dep': ['b']},
            'task_p2': lambda: {'actions': None, 'task_dep': ['c']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p2', 'p1']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['c', 'b', 'kid'], self.log)

    def test_shared_task_dep_listed_once(self):
        ns = {
            'task_x': lambda: {'actions': [self.rec('x')]},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'task_dep': ['x'], 'inherits': ['p']},
        }
        self.assertEqual(['x'], self.info_block(ns, 'kid', 'task_dep'))

    def test_setup_own_entries_then_parents(self):
        ns = {
            'task_s1': lambda: {'actions': [self.rec('s1')]},
            'task_s2': lambda: {'actions': [self.rec('s2')]},
            'task_p': lambda: {'actions': None, 'setup': ['s2']},
            'task_s3': lambda: {'actions': [self.rec('s3')]},
            'task_q': lambda: {'actions': None, 'setup': ['s3', 's1']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'setup': ['s1'], 'inherits': ['p', 'q']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['s1', 's2', 's3', 'kid'], self.log)
        self.assertEqual(['s1', 's2', 's3'],
                         self.info_block(ns, 'kid', 'setup_tasks'))

    def test_file_dep_combined_and_drives_uptodate(self):
        self.write('one.txt', '1')
        self.write('two.txt', '2')
        one, two = self.path('one.txt'), self.path('two.txt')
        ns = {
            'task_p': lambda: {'actions': None, 'file_dep': [two]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'file_dep': [one], 'inherits': ['p']},
        }
        self.assertEqual(sorted([one, two]),
                         sorted(self.info_block(ns, 'kid', 'file_dep')))
        self.doit(ns, 'run', 'kid')
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['kid'], self.log)
        self.write('two.txt', 'changed')
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['kid', 'kid'], self.log)

    def test_calc_dep_combined(self):
        ns = {
            'task_calc': lambda: {'actions': [self.rec('calc')]},
            'task_p': lambda: {'actions': None, 'calc_dep': ['calc']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['calc', 'kid'], self.log)
        self.assertEqual(['calc'], self.info_block(ns, 'kid', 'calc_dep'))

    def test_inherited_wildcard_selects_subtasks(self):
        def task_lint():
            for name in ('one', 'two'):
                yield {'name': name, 'actions': [self.rec('lint:' + name)]}
        ns = {
            'task_lint': task_lint,
            'task_p': lambda: {'actions': None, 'task_dep': ['lint:*']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['lint:one', 'lint:two', 'kid'], self.log)

    def test_inherited_file_dep_on_target_adds_dependency(self):
        out_file = self.path('gen.out')

        def generate():
            self.log.append('gen')
            with open(out_file, 'w') as fh:
                fh.write('x')
        ns = {
            'task_gen': lambda: {'actions': [generate],
                                 'targets': [out_file]},
            'task_p': lambda: {'actions': None, 'file_dep': [out_file]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['gen', 'kid'], self.log)


class TestInheritChecks(InheritsTestCase):

    def test_inherited_config_changed_is_recorded_for_child(self):
        check = config_changed({'mode': 'fast'})
        ns = {
            'task_p': lambda: {'actions': None, 'uptodate': [check]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        self.doit(ns, 'run', 'kid')
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['kid'], self.log)

    def test_inherited_false_check_keeps_task_running(self):
        ns = {
            'task_p': lambda: {'actions': None, 'uptodate': [False]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'uptodate': [True], 'inherits': ['p']},
        }
        self.doit(ns, 'run', 'kid')
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['kid', 'kid'], self.log)

    def test_inherited_getargs_value_and_source(self):
        def produce():
            self.log.append('src')
            return {'value': 'from-src'}

        def consume(value):
            self.log.append('kid:' + value)
        ns = {
            'task_src': lambda: {'actions': [produce]},
            'task_p': lambda: {'actions': None,
                               'getargs': {'value': ('src', 'value')}},
            'task_kid': lambda: {'actions': [consume], 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['src', 'kid:from-src'], self.log)

    def test_inherited_getargs_checks_like_declared(self):
        def produce():
            return {'value': 'same'}

        def consume(value):
            self.log.append(value)
        ns = {
            'task_src': lambda: {'actions': [produce]},
            'task_p': lambda: {'actions': None,
                               'getargs': {'value': ('src', 'value')}},
            'task_kid': lambda: {'actions': [consume], 'inherits': ['p']},
        }
        self.doit(ns, 'run', 'kid')
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['same'], self.log)

    def test_own_getargs_entry_wins(self):
        def produce(label):
            def action():
                return {'value': label}
            return action

        def consume(value):
            self.log.append(value)
        ns = {
            'task_src1': lambda: {'actions': [produce('one')]},
            'task_src2': lambda: {'actions': [produce('two')]},
            'task_p': lambda: {'actions': None,
                               'getargs': {'value': ('src1', 'value')}},
            'task_kid': lambda: {'actions': [consume],
                                 'getargs': {'value': ('src2', 'value')},
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['two'], self.log)

    def test_getargs_first_parent_in_order_wins(self):
        def produce(label):
            def action():
                return {'value': label}
            return action

        def consume(value):
            self.log.append(value)
        ns = {
            'task_src1': lambda: {'actions': [produce('one')]},
            'task_src2': lambda: {'actions': [produce('two')]},
            'task_p1': lambda: {'actions': None,
                                'getargs': {'value': ('src1', 'value')}},
            'task_p2': lambda: {'actions': None,
                                'getargs': {'value': ('src2', 'value')}},
            'task_kid': lambda: {'actions': [consume],
                                 'inherits': ['p2', 'p1']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['two'], self.log)


class TestInheritOptions(InheritsTestCase):

    def ns_with_params(self):
        def show(level, color):
            self.log.append('%s/%s' % (level, color))
        return {
            'task_p1': lambda: {'actions': None, 'params': [
                {'name': 'level', 'long': 'level', 'default': 'low'},
                {'name': 'color', 'long': 'color', 'default': 'red'}]},
            'task_p2': lambda: {'actions': None, 'params': [
                {'name': 'color', 'long': 'color', 'default': 'blue'}]},
            'task_kid': lambda: {'actions': [show],
                                 'inherits': ['p2', 'p1']},
        }

    def test_inherited_option_defaults_first_parent_wins(self):
        code, _ = self.doit(self.ns_with_params(), 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['low/blue'], self.log)

    def test_inherited_option_accepted_on_command_line(self):
        code, _ = self.doit(self.ns_with_params(), 'run', 'kid',
                            '--level', 'high')
        self.assertEqual(0, code)
        self.assertEqual(['high/blue'], self.log)

    def test_task_params_options_inherited(self):
        @task_params([{'name': 'flavor', 'long': 'flavor',
                       'default': 'plain'}])
        def task_p(flavor):
            return {'actions': None}

        def taste(flavor):
            self.log.append(flavor)
        ns = {
            'task_p': task_p,
            'task_kid': lambda: {'actions': [taste], 'inherits': ['p']},
        }
        self.doit(ns, 'run', 'kid')
        self.doit(ns, 'run', 'kid', '--flavor', 'spicy')
        self.assertEqual(['plain', 'spicy'], self.log)

    def test_own_option_wins(self):
        def show(level):
            self.log.append(level)
        ns = {
            'task_p': lambda: {'actions': None, 'params': [
                {'name': 'level', 'long': 'level', 'default': 'low'}]},
            'task_kid': lambda: {'actions': [show], 'params': [
                {'name': 'level', 'long': 'level', 'default': 'mid'}],
                'inherits': ['p']},
        }
        self.doit(ns, 'run', 'kid')
        self.assertEqual(['mid'], self.log)

    def test_help_lists_inherited_option(self):
        code, out = self.doit(self.ns_with_params(), 'help', 'kid')
        self.assertEqual(0, code)
        self.assertIn('--level', out)

    def test_meta_merged_by_key(self):
        ns = {
            'task_p1': lambda: {'actions': None, 'meta': {'a': 1, 'b': 2}},
            'task_p2': lambda: {'actions': None, 'meta': {'b': 3, 'c': 4}},
            'task_kid': lambda: {'actions': None, 'meta': {'a': 0},
                                 'inherits': ['p1', 'p2']},
        }
        self.assertEqual("{'a': 0, 'b': 2, 'c': 4}",
                         self.info_line(ns, 'kid', 'meta'))


class TestInheritScalars(InheritsTestCase):

    def test_doc_from_parent_when_none_of_its_own(self):
        def task_p():
            return {'actions': None, 'doc': 'shared build step'}

        def task_kid():
            return {'actions': None, 'inherits': ['p']}
        self.assertEqual('shared build step',
                         self.list_doc({'task_p': task_p,
                                        'task_kid': task_kid}, 'kid'))

    def test_own_doc_value_wins(self):
        def task_p():
            return {'actions': None, 'doc': 'shared build step'}

        def task_kid():
            return {'actions': None, 'doc': 'kid step', 'inherits': ['p']}
        self.assertEqual('kid step',
                         self.list_doc({'task_p': task_p,
                                        'task_kid': task_kid}, 'kid'))

    def test_creator_docstring_counts_as_own_doc(self):
        def task_p():
            return {'actions': None, 'doc': 'shared build step'}

        def task_kid():
            return {'actions': None, 'inherits': ['p']}
        task_kid.__doc__ = 'kid docstring'
        self.assertEqual('kid docstring',
                         self.list_doc({'task_p': task_p,
                                        'task_kid': task_kid}, 'kid'))

    def test_blank_doc_is_not_own_doc(self):
        def task_p():
            return {'actions': None, 'doc': 'shared build step'}

        def task_kid():
            return {'actions': None, 'doc': '  \n  ', 'inherits': ['p']}
        self.assertEqual('shared build step',
                         self.list_doc({'task_p': task_p,
                                        'task_kid': task_kid}, 'kid'))

    def test_verbosity_inherited(self):
        ns = {
            'task_p': lambda: {'actions': None, 'verbosity': 2},
            'task_kid': lambda: {'actions': None, 'inherits': ['p']},
        }
        self.assertEqual('2', self.info_line(ns, 'kid', 'verbosity'))

    def test_verbosity_zero_is_kept(self):
        def speak():
            print('spoken-by-kid')
        ns = {
            'task_p': lambda: {'actions': None, 'verbosity': 2},
            'task_kid': lambda: {'actions': [speak], 'verbosity': 0,
                                 'inherits': ['p']},
        }
        code, out = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertNotIn('spoken-by-kid', out)

    def test_first_parent_after_its_own_inheritance_wins(self):
        def speak():
            print('spoken-by-kid')
        ns = {
            'task_base': lambda: {'actions': None, 'verbosity': 0},
            'task_p1': lambda: {'actions': None, 'inherits': ['base']},
            'task_p2': lambda: {'actions': None, 'verbosity': 2},
            'task_kid': lambda: {'actions': [speak],
                                 'inherits': ['p1', 'p2']},
        }
        code, out = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertNotIn('spoken-by-kid', out)


class TestInheritExclusions(InheritsTestCase):

    def test_actions_not_inherited(self):
        ns = {
            'task_p': lambda: {'actions': [self.rec('p')]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['kid'], self.log)

    def test_targets_not_inherited(self):
        target = self.path('p.out')
        ns = {
            'task_p': lambda: {'actions': None, 'targets': [target]},
            'task_kid': lambda: {'actions': None, 'inherits': ['p']},
        }
        self.assertEqual([], self.info_block(ns, 'kid', 'targets'))
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)

    def test_clean_not_inherited(self):
        ns = {
            'task_p': lambda: {'actions': None, 'clean': [self.rec('clean-p')]},
            'task_kid': lambda: {'actions': None,
                                 'clean': [self.rec('clean-kid')],
                                 'inherits': ['p']},
        }
        self.doit(ns, 'clean', 'kid')
        self.assertEqual(['clean-kid'], self.log)

    def test_clean_dep_follows_inherited_task_dep(self):
        ns = {
            'task_x': lambda: {'actions': None, 'clean': [self.rec('clean-x')]},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_kid': lambda: {'actions': None, 'inherits': ['p']},
        }
        self.doit(ns, 'clean', '--clean-dep', 'kid')
        self.assertEqual(['clean-x'], self.log)

    def test_teardown_not_inherited(self):
        ns = {
            'task_p': lambda: {'actions': None,
                               'teardown': [self.rec('down-p')]},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['kid'], self.log)

    def test_watch_not_inherited(self):
        ns = {
            'task_p': lambda: {'actions': None, 'watch': ['src']},
            'task_kid': lambda: {'actions': None, 'inherits': ['p']},
        }
        self.assertEqual([], self.info_block(ns, 'kid', 'watch'))

    def test_title_io_and_pos_arg_not_inherited(self):
        parent = Task('p', None, title=lambda task: 'custom',
                      io={'capture': False},
                      params=[{'name': 'files', 'default': []}],
                      pos_arg='files')
        kid = Task('kid', None, inherits=['p'])
        TaskControl([parent, kid])
        self.assertEqual('kid', kid.title())
        self.assertTrue(kid.io.capture)
        self.assertIsNone(kid.pos_arg)

    def test_parent_not_modified(self):
        ns = {
            'task_x': lambda: {'actions': None},
            'task_y': lambda: {'actions': None},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_kid': lambda: {'actions': None, 'task_dep': ['y'],
                                 'inherits': ['p']},
        }
        self.assertEqual(['x'], self.info_block(ns, 'p', 'task_dep'))


class TestInheritResolution(InheritsTestCase):

    def test_chain_of_parents(self):
        ns = {
            'task_x': lambda: {'actions': None},
            'task_y': lambda: {'actions': None},
            'task_z': lambda: {'actions': None},
            'task_base': lambda: {'actions': None, 'task_dep': ['z'],
                                  'meta': {'level': 'base'}},
            'task_mid': lambda: {'actions': None, 'task_dep': ['y'],
                                 'inherits': ['base']},
            'task_kid': lambda: {'actions': None, 'task_dep': ['x'],
                                 'inherits': ['mid']},
        }
        self.assertEqual(['x', 'y', 'z'],
                         self.info_block(ns, 'kid', 'task_dep'))
        self.assertEqual("{'level': 'base'}", self.info_line(ns, 'kid', 'meta'))

    def test_shared_ancestor_counted_once_at_first_position(self):
        ns = {
            'task_a': lambda: {'actions': None},
            'task_b': lambda: {'actions': None},
            'task_x': lambda: {'actions': None},
            'task_base': lambda: {'actions': None, 'task_dep': ['x']},
            'task_p1': lambda: {'actions': None, 'task_dep': ['a'],
                                'inherits': ['base']},
            'task_p2': lambda: {'actions': None, 'task_dep': ['b'],
                                'inherits': ['base']},
            'task_kid': lambda: {'actions': None, 'inherits': ['p1', 'p2']},
        }
        self.assertEqual(['a', 'x', 'b'],
                         self.info_block(ns, 'kid', 'task_dep'))

    def test_subtask_inherits(self):
        def task_group():
            yield {'name': 'one', 'actions': [self.rec('one')],
                   'inherits': ['p']}
        ns = {
            'task_x': lambda: {'actions': [self.rec('x')]},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_group': task_group,
        }
        code, _ = self.doit(ns, 'run', 'group:one')
        self.assertEqual(0, code)
        self.assertEqual(['x', 'one'], self.log)

    def test_inherit_from_subtask_by_full_name(self):
        def task_group():
            yield {'name': 'one', 'actions': [self.rec('one')],
                   'task_dep': ['x']}
        ns = {
            'task_x': lambda: {'actions': [self.rec('x')]},
            'task_group': task_group,
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['group:one']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['x', 'kid'], self.log)

    def test_inherit_from_group_task(self):
        def task_group():
            for name in ('one', 'two'):
                yield {'name': name, 'actions': [self.rec(name)]}
        ns = {
            'task_group': task_group,
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['group']},
        }
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['one', 'two', 'kid'], self.log)

    def test_delayed_task_inherits_when_generated(self):
        @create_after(executed='trigger')
        def task_late():
            return {'actions': [self.rec('late')], 'inherits': ['p']}
        ns = {
            'task_trigger': lambda: {'actions': [self.rec('trigger')]},
            'task_x': lambda: {'actions': [self.rec('x')]},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_late': task_late,
        }
        code, _ = self.doit(ns, 'run', 'late')
        self.assertEqual(0, code)
        self.assertEqual(['trigger', 'x', 'late'], self.log)

    def test_task_control_resolves_task_objects(self):
        parent = Task('p', None, file_dep=['p.txt'], task_dep=['x'],
                      doc='parent doc', verbosity=2)
        kid = Task('kid', None, file_dep=['kid.txt'], inherits=['p'])
        x = Task('x', None)
        tc = TaskControl([x, parent, kid])
        resolved = tc.tasks['kid']
        self.assertEqual({'kid.txt', 'p.txt'}, set(resolved.file_dep))
        self.assertEqual(['x'], resolved.task_dep)
        self.assertEqual('parent doc', resolved.doc)
        self.assertEqual(2, resolved.verbosity)
        self.assertEqual(['x'], tc.tasks['p'].task_dep)


class TestInheritErrors(InheritsTestCase):

    def test_unknown_parent(self):
        kid = Task('kid', None, inherits=['missing'])
        self.assertRaises(InvalidTask, TaskControl, [kid])

    def test_unknown_parent_from_command_line(self):
        valid = {
            'task_x': lambda: {'actions': [self.rec('x')]},
            'task_p': lambda: {'actions': None, 'task_dep': ['x']},
            'task_kid': lambda: {'actions': [self.rec('kid')],
                                 'inherits': ['p']},
        }
        code, _ = self.doit(valid, 'run', 'kid')
        self.assertEqual(0, code)
        self.assertEqual(['x', 'kid'], self.log)
        ns = {'task_kid': lambda: {'actions': None, 'inherits': ['missing']}}
        code, _ = self.doit(ns, 'list')
        self.assertEqual(3, code)
        code, _ = self.doit(ns, 'run', 'kid')
        self.assertEqual(3, code)

    def test_cycle(self):
        one = Task('one', None, inherits=['two'])
        two = Task('two', None, inherits=['one'])
        self.assertRaises(InvalidDodoFile, TaskControl, [one, two])

    def test_self_inheritance(self):
        one = Task('one', None, inherits=['one'])
        self.assertRaises(InvalidDodoFile, TaskControl, [one])

    def test_cycle_from_command_line(self):
        valid = {
            'task_one': lambda: {'actions': None, 'inherits': ['two']},
            'task_two': lambda: {'actions': None, 'doc': 'two doc'},
        }
        self.assertEqual('two doc', self.list_doc(valid, 'one'))
        ns = {
            'task_one': lambda: {'actions': None, 'inherits': ['two']},
            'task_two': lambda: {'actions': None, 'inherits': ['three']},
            'task_three': lambda: {'actions': None, 'inherits': ['one']},
        }
        code, _ = self.doit(ns, 'info', 'one')
        self.assertEqual(3, code)

    def test_inherits_of_another_type_is_rejected(self):
        self.assertRaises(InvalidTask, Task, 'kid', None, inherits='p')

    def test_inherits_entries_must_be_strings(self):
        self.assertRaises(InvalidTask, Task, 'kid', None, inherits=['p', 3])

    def test_tuple_accepted(self):
        parent = Task('p', None, doc='from tuple')
        kid = Task('kid', None, inherits=('p',))
        TaskControl([parent, kid])
        self.assertEqual('from tuple', kid.doc)
