import os
import inspect
import unittest
from operator import attrgetter

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, DelayedLoader, Task
from doit.loader import flat_generator, get_module
from doit.loader import load_tasks, load_doit_config, generate_tasks
from doit.loader import create_after, task_params

from tests.support import RestoreCwdMixin

# tests/ directory where loader_sample.py and data/ live
TEST_PATH = os.path.join(os.path.dirname(__file__), '..', 'tests')


class TestFlatGenerator(unittest.TestCase):
    def test_nested(self):
        def myg(items):
            for x in items:
                yield x
        flat = flat_generator(myg([1, myg([2, myg([3, myg([4, myg([5])])])])]))
        self.assertEqual([1, 2, 3, 4, 5], [f[0] for f in flat])


class TestGetModule(RestoreCwdMixin, unittest.TestCase):
    def testAbsolutePath(self):
        fileName = os.path.join(TEST_PATH, "loader_sample.py")
        dodo_module = get_module(fileName)
        self.assertTrue(hasattr(dodo_module, 'task_xxx1'))

    def testRelativePath(self):
        # test relative import but test should still work from any path
        # so change cwd.
        this_path = os.path.join(TEST_PATH, '..')
        os.chdir(os.path.abspath(this_path))
        fileName = "tests/loader_sample.py"
        dodo_module = get_module(fileName)
        self.assertTrue(hasattr(dodo_module, 'task_xxx1'))

    def testWrongFileName(self):
        fileName = os.path.join(TEST_PATH, "i_dont_exist.py")
        self.assertRaises(InvalidDodoFile, get_module, fileName)

    def testInParentDir(self):
        os.chdir(os.path.join(TEST_PATH, "data"))
        fileName = "loader_sample.py"
        self.assertRaises(InvalidDodoFile, get_module, fileName)
        get_module(fileName, seek_parent=True)
        # cwd is changed to location of dodo.py
        self.assertEqual(os.getcwd(), os.path.dirname(os.path.abspath(fileName)))

    def testWrongFileNameInParentDir(self):
        os.chdir(os.path.join(TEST_PATH, "data"))
        fileName = os.path.join("i_dont_exist.py")
        self.assertRaises(InvalidDodoFile, get_module, fileName, seek_parent=True)

    def testInvalidCwd(self):
        fileName = os.path.join(TEST_PATH, "loader_sample.py")
        cwd = os.path.join(TEST_PATH, "dataX")
        self.assertRaises(InvalidCommand, get_module, fileName, cwd)


class TestLoadTasks(unittest.TestCase):

    def _make_dodo(self):
        def task_xxx1():
            """task doc"""
            return {'actions': ['do nothing']}

        def task_yyy2():
            return {'actions': None}

        def task_meta():
            return {
                'actions': ['do nothing'],
                'meta': {'a': ['b', 'c']},
            }

        def bad_seed(): pass
        task_nono = 5
        task_nono  # pyflakes
        return locals()

    def testNormalCase(self):
        dodo = self._make_dodo()
        task_list = load_tasks(dodo)
        self.assertEqual(3, len(task_list))
        self.assertEqual('xxx1', task_list[0].name)
        self.assertEqual('yyy2', task_list[1].name)
        self.assertEqual('meta', task_list[2].name)

    def testCreateAfterDecorator(self):
        @create_after('yyy2')
        def task_zzz3():  # pragma: no cover
            pass

        # create_after annotates the function
        self.assertIsInstance(task_zzz3.doit_create_after, DelayedLoader)
        self.assertEqual(task_zzz3.doit_create_after.task_dep, 'yyy2')

    def testInitialLoadDelayedTask(self):
        dodo = self._make_dodo()
        @create_after('yyy2')
        def task_zzz3():  # pragma: no cover
            raise Exception('Cant be executed on load phase')
        dodo['task_zzz3'] = task_zzz3

        # placeholder task is created with `loader` attribute
        task_list = load_tasks(dodo, allow_delayed=True)
        z_task = [t for t in task_list if t.name == 'zzz3'][0]
        self.assertEqual(z_task.loader.task_dep, 'yyy2')
        self.assertEqual(z_task.loader.creator, task_zzz3)

    def testInitialLoadDelayedTask_no_delayed(self):
        dodo = self._make_dodo()
        @create_after('yyy2')
        def task_zzz3():
            yield {'basename': 'foo', 'actions': None}
            yield {'basename': 'bar', 'actions': None}
        dodo['task_zzz3'] = task_zzz3

        # load tasks as done by the `list` command
        task_list = load_tasks(dodo, allow_delayed=False)
        tasks = {t.name: t for t in task_list}
        self.assertNotIn('zzz3', tasks)
        self.assertIsNone(tasks['foo'].loader)
        self.assertIsNone(tasks['bar'].loader)

    def testInitialLoadDelayedTask_creates(self):
        dodo = self._make_dodo()
        @create_after('yyy2', creates=['foo', 'bar'])
        def task_zzz3():  # pragma: no cover
            '''not loaded task doc'''
            raise Exception('Cant be executed on load phase')
        dodo['task_zzz3'] = task_zzz3

        # placeholder task is created with `loader` attribute
        task_list = load_tasks(dodo, allow_delayed=True)
        tasks = {t.name: t for t in task_list}
        self.assertNotIn('zzz3', tasks)
        f_task = tasks['foo']
        self.assertEqual(f_task.loader.task_dep, 'yyy2')
        self.assertEqual(f_task.loader.creator, task_zzz3)
        self.assertEqual(tasks['bar'].loader.task_dep,
                         tasks['foo'].loader.task_dep)
        self.assertEqual(tasks['foo'].doc, 'not loaded task doc')

        # make sure doit can be executed more then once in single process GH#381
        list2 = load_tasks(dodo, allow_delayed=True)
        tasks2 = {t.name: t for t in list2}
        self.assertIsNot(tasks['bar'].loader, tasks2['bar'].loader)

    def testCreateAfterDecoratorOnMethod(self):
        'Check that class-defined tasks are loaded as bound methods'
        class Tasks:
            @create_after('yyy2')
            def task_zzz3():  # pragma: no cover
                pass

        # create_after annotates the function
        task_list = load_tasks(
            {'task_zzz3': Tasks().task_zzz3}, allow_delayed=True)
        tasks = {t.name: t for t in task_list}
        task_zzz3 = tasks['zzz3']
        self.assertIsInstance(task_zzz3.loader, DelayedLoader)
        # check creator is a bound method, not a plain function
        self.assertIsNotNone(
            getattr(task_zzz3.loader.creator, '__self__', None))

    def testCreateAfterDecoratorOnMethodWithParams(self):
        'Check that class-defined tasks support the creates argument of @create_after'
        dodo = self._make_dodo()
        class Tasks:
            @create_after('yyy2', creates=['foo', 'bar'])
            def task_zzz3():  # pragma: no cover
                '''not loaded task doc'''
                raise Exception('Cant be executed on load phase')

        # placeholder task is created with `loader` attribute
        task_list = load_tasks(
            {'task_zzz3': Tasks().task_zzz3}, allow_delayed=True)
        tasks = {t.name: t for t in task_list}
        self.assertNotIn('zzz3', tasks)
        f_task = tasks['foo']
        self.assertEqual(f_task.loader.task_dep, 'yyy2')
        self.assertIsNotNone(
            getattr(f_task.loader.creator, '__self__', None))
        # loaders are not the same because of #381 (multiple execution on same process)
        # But this is not a problem because once the task already exists, the loader is just not used.
        # assert tasks['bar'].loader is tasks['foo'].loader
        self.assertEqual(tasks['foo'].doc, 'not loaded task doc')

    def testNameInBlacklist(self):
        dodo_module = {'task_cmd_name': lambda: None}
        self.assertRaises(InvalidDodoFile, load_tasks,
                          dodo_module, ['cmd_name'])

    def testDocString(self):
        dodo = self._make_dodo()
        task_list = load_tasks(dodo)
        self.assertEqual("task doc", task_list[0].doc)

    def testMetaInfo(self):
        dodo = self._make_dodo()
        task_list = load_tasks(dodo)
        self.assertEqual(task_list[2].meta, {'a': ['b', 'c']})

    def testUse_create_doit_tasks(self):
        def original(): pass
        def creator():
            return {'actions': ['do nothing'], 'file_dep': ['foox']}
        original.create_doit_tasks = creator
        task_list = load_tasks({'x': original})
        self.assertEqual(1, len(task_list))
        self.assertEqual(set(['foox']), task_list[0].file_dep)

    def testUse_create_doit_tasks_class_method(self):
        class Foo(object):
            def __init__(self):
                self.create_doit_tasks = self._create_doit_tasks
            def _create_doit_tasks(self):
                return {'actions': ['do nothing'], 'file_dep': ['fooy']}

        task_list = load_tasks({'Foo': Foo, 'foo': Foo()})
        self.assertEqual(len(task_list), 1)
        self.assertEqual(task_list[0].file_dep, set(['fooy']))

    def testUse_create_doit_tasks_basename_kwargs(self):
        class Foo(object):
            def __init__(self):
                @task_params([{"name": "t", "default": None, "type": list}])
                def creator(**kwargs):
                    return self._create_doit_tasks(**kwargs)
                creator.basename = 'my-foo'
                self.create_doit_tasks = creator

            def _create_doit_tasks(self, **kwargs):
                return {'actions': ['do nothing'], 'file_dep': ['fooy'],
                        'targets': kwargs['t']}

        task_list = load_tasks({'Foo': Foo, 'foo': Foo()},
                               task_opts={'my-foo': {'t': ['bar']}})
        self.assertEqual(len(task_list), 1)
        self.assertEqual(task_list[0].name, 'my-foo')
        self.assertEqual(task_list[0].targets, ['bar'])

    def testUse_object_methods(self):
        class Dodo(object):
            def foo(self):  # pragma: no cover
                pass

            def task_method1(self):
                return {'actions': None}

            def task_method2(self):
                return {'actions': None}

        methods = dict(inspect.getmembers(Dodo()))
        task_list = load_tasks(methods)
        self.assertEqual(2, len(task_list))
        self.assertEqual('method1', task_list[0].name)
        self.assertEqual('method2', task_list[1].name)


class TestTaskGeneratorParams(unittest.TestCase):

    def test_task_params_annotations(self):
        params = [{"name": "foo", "default": "bar", "long": "foo"}]
        func = task_params(params)(lambda: 1)
        self.assertEqual(func._task_creator_params, params)

    def test_default(self):
        'Ensure that a task parameter can be passed to the task generator.'

        @task_params([{"name": "foo", "default": "bar", "long": "foo"}])
        def task_foo(foo):
            return {
                'actions': [],
                'doc': foo
            }
        task_list = load_tasks({'task_foo': task_foo})
        task = task_list.pop()
        self.assertEqual(task.doc, 'bar')
        task.init_options()
        self.assertEqual(task.options['foo'], 'bar')

    def test_args(self):
        'Ensure that a task generator parameter can be set from the command line.'
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        args = ['foo', '--fp=from_arg']
        task_list = load_tasks({'task_foo': task_foo}, args=args)
        task = task_list.pop()
        self.assertEqual(task.doc, 'from_arg')

    def test_call_api(self):
        'Ensure that a task generator parameter can be set from direct API call'
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        args = ['foo']
        task_opts = {'foo': {'fp': 'from_api'}}
        task_list = load_tasks({'task_foo': task_foo}, args=args,
                               task_opts=task_opts)
        task = task_list.pop()
        self.assertEqual(task.doc, 'from_api')

    def test_args_second(self):
        def task_bar():
            return {'actions': []}

        @task_params([{"name": "foo", "default": "placeholder",
                       "long": "foo"}])
        def task_foo(foo):
            return {
                'actions': [],
                'doc': foo
            }
        args = ['bar', 'foo', '--foo=from_arg']
        task_list = load_tasks({'task_foo': task_foo, 'task_bar': task_bar},
                               args=args)
        self.assertEqual(len(task_list), 2)
        bar, foo = sorted(task_list, key=attrgetter('name'))
        self.assertEqual(foo.name, 'foo')
        self.assertEqual(foo.doc, 'from_arg')

    def test_config(self):
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        config = {'task:foo': {'fp': 'from_config'}}
        task_list = load_tasks({'task_foo': task_foo}, args=(),
                               config=config)
        task = task_list.pop()
        self.assertEqual(task.doc, 'from_config')
        # config is overwritten from args
        args = ['foo', '--fp=from_arg']
        task_list2 = load_tasks({'task_foo': task_foo}, args=args,
                                config=config)
        task2 = task_list2.pop()
        self.assertEqual(task2.doc, 'from_arg')

    def test_method(self):
        'Ensure that a task parameter can be passed to the task generator defined as a class method.'
        class Tasks(object):
            @task_params([{"name": "param1", "default": "placeholder",
                           "long": "param1"}])
            def task_foo(self, param1):
                for i in range(2):
                    yield {
                        'name': 'subtask' + str(i),
                        'actions': [],
                        'doc': param1,
                    }

        foo = Tasks().task_foo
        task_list = load_tasks({'task_foo': foo},
                               args=('foo', '--param1=my_val'))

        self.assertEqual(len(task_list), 3)
        tasks = {t.name: t for t in task_list}

        self.assertEqual(len(tasks['foo'].params), 0)
        self.assertEqual(len(tasks['foo'].creator_params), 1)
        self.assertEqual(tasks['foo'].doc, '')

        self.assertEqual(len(tasks['foo:subtask0'].params), 0)
        self.assertEqual(tasks['foo:subtask0'].doc, 'my_val')

    def test_delayed(self):
        @create_after()
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        args = ['foo', '--fp=from_arg']
        task_list = load_tasks({'task_foo': task_foo}, allow_delayed=True,
                               args=args)
        task = task_list.pop()
        self.assertEqual(task.name, 'foo')
        self.assertEqual(task.loader.kwargs, {'fp': 'from_arg'})
        self.assertEqual(len(task.creator_params), 1)

    def test_dup_param(self):
        'Ensure that `params` field and @task_params definitions are prohibited'
        @task_params([{"name": "foo", "default": "decorator", "long": "foo"}])
        def task_dup(foo):
            return {
                'actions': [],
                'params': [{"name": "bar", "default": "dict",
                             "long": "bar"}],
            }

        with self.assertRaises(InvalidTask) as cm:
            load_tasks({'task_dup': task_dup})
        self.assertIn('attribute can not be used in conjuction with',
                      str(cm.exception))


class TestDodoConfig(unittest.TestCase):

    def testConfigType_Error(self):
        self.assertRaises(InvalidDodoFile, load_doit_config,
                          {'DOIT_CONFIG': 'abc'})

    def testConfigDict_Ok(self):
        config = load_doit_config({'DOIT_CONFIG': {'verbose': 2}})
        self.assertEqual({'verbose': 2}, config)

    def testDefaultConfig_Dict(self):
        config = load_doit_config({'whatever': 2})
        self.assertEqual({}, config)


class TestGenerateTaskInvalid(unittest.TestCase):
    def testInvalidValue(self):
        self.assertRaises(InvalidTask, generate_tasks, "dict", 'xpto 14')


class TestGenerateTaskNone(unittest.TestCase):
    def testEmpty(self):
        tasks = generate_tasks('xx', None)
        self.assertEqual(len(tasks), 0)


class TestGenerateTasksSingle(unittest.TestCase):
    def testDict(self):
        tasks = generate_tasks("my_name", {'actions': ['xpto 14']})
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual("my_name", tasks[0].name)

    def testTaskObj(self):
        tasks = generate_tasks("foo", Task('bar', None))
        self.assertEqual(1, len(tasks))
        self.assertEqual(tasks[0].name, 'bar')

    def testBaseName(self):
        tasks = generate_tasks("function_name", {
            'basename': 'real_task_name',
            'actions': ['xpto 14']
        })
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual("real_task_name", tasks[0].name)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        self.assertRaises(InvalidTask, generate_tasks, "my_name",
                          {'actions': ['xpto 14'], 'name': 'bla bla'})

    def testUseDocstring(self):
        tasks = generate_tasks("dict", {'actions': ['xpto 14']}, "my doc")
        self.assertEqual("my doc", tasks[0].doc)

    def testDocstringNotUsed(self):
        mytask = {'actions': ['xpto 14'], 'doc': 'from dict'}
        tasks = generate_tasks("dict", mytask, "from docstring")
        self.assertEqual("from dict", tasks[0].doc)


class TestGenerateTasksGenerator(unittest.TestCase):

    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name': str(i), 'actions': ["xpto -%d" % i]}
        tasks = generate_tasks("xpto", f_xpto())
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual(4, len(tasks))
        self.assertIsNone(tasks[0].subtask_of)
        self.assertEqual("xpto:0", tasks[0].task_dep[0])
        self.assertEqual("xpto:0", tasks[1].name)
        self.assertEqual(tasks[1].subtask_of, 'xpto')

    def testMultiLevelGenerator(self):
        def f_xpto(base_name):
            """second level docstring"""
            for i in range(3):
                name = "%s-%d" % (base_name, i)
                yield {'name': name, 'actions': ["xpto -%d" % i]}
        def f_first_level():
            for i in range(2):
                yield f_xpto(str(i))
        tasks = generate_tasks("xpto", f_first_level())
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual(7, len(tasks))
        self.assertIsNone(tasks[0].subtask_of)
        self.assertEqual(f_xpto.__doc__, tasks[0].doc)
        self.assertEqual(tasks[1].subtask_of, 'xpto')
        self.assertEqual("xpto:0-0", tasks[1].name)
        self.assertEqual("xpto:1-2", tasks[-1].name)

    def testGeneratorReturnTaskObj(self):
        def foo(base_name):
            for i in range(3):
                name = "%s-%d" % (base_name, i)
                yield Task(name, actions=["xpto -%d" % i])
        tasks = generate_tasks("foo", foo('bar'))
        self.assertEqual(3, len(tasks))
        self.assertEqual(tasks[0].name, 'bar-0')
        self.assertEqual(tasks[1].name, 'bar-1')
        self.assertEqual(tasks[2].name, 'bar-2')

    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d" % i
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name': str(i)}
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions': ["xpto -%d" % i]}
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasename(self):
        def f_xpto():
            for i in range(3):
                yield {'basename': str(i), 'actions': ["xpto"]}
        tasks = sorted(generate_tasks("xpto", f_xpto()),
                       key=lambda t: t.name)
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual(3, len(tasks))
        self.assertEqual("0", tasks[0].name)
        self.assertIsNone(tasks[0].subtask_of)
        self.assertIsNone(tasks[1].subtask_of)

    def testGeneratorBasenameName(self):
        def f_xpto():
            for i in range(3):
                yield {'basename': 'xpto', 'name': str(i),
                       'actions': ["a"]}
        tasks = sorted(generate_tasks("f_xpto", f_xpto()))
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual(4, len(tasks))
        self.assertEqual("xpto", tasks[0].name)
        self.assertEqual("xpto:0", tasks[1].name)
        self.assertIsNone(tasks[0].subtask_of)
        self.assertEqual(tasks[1].subtask_of, 'xpto')

    def testGeneratorBasenameCanNotRepeat(self):
        def f_xpto():
            for i in range(3):
                yield {'basename': 'again', 'actions': ["xpto"]}
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasenameCanNotRepeatNonGroup(self):
        def f_xpto():
            yield {'basename': 'xpto', 'actions': ["a"]}
            for i in range(3):
                yield {'name': str(i),
                       'actions': ["a"]}
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorNameCanNotRepeat(self):
        def f_xpto():
            yield {'basename': 'bn', 'name': 'xxx', 'actions': ["xpto"]}
            yield {'basename': 'bn', 'name': 'xxx', 'actions': ["xpto2"]}
        self.assertRaises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDocString(self):
        def f_xpto():
            "the doc"
            for i in range(3):
                yield {'name': str(i), 'actions': ["xpto -%d" % i]}
        tasks = sorted(generate_tasks("xpto", f_xpto(), f_xpto.__doc__))
        self.assertEqual("the doc", tasks[0].doc)

    def testGeneratorWithNoTasks(self):
        def f_xpto():
            for x in []: yield x
        tasks = generate_tasks("xpto", f_xpto())
        self.assertEqual(1, len(tasks))
        self.assertEqual("xpto", tasks[0].name)
        self.assertIsNone(tasks[0].subtask_of)

    def testGeneratorBaseOnly(self):
        def f_xpto():
            yield {'basename': 'xpto', 'name': None, 'doc': 'xxx doc'}
        tasks = sorted(generate_tasks("f_xpto", f_xpto()))
        self.assertEqual(1, len(tasks))
        self.assertIsInstance(tasks[0], Task)
        self.assertEqual("xpto", tasks[0].name)
        self.assertTrue(tasks[0].has_subtask)
        self.assertEqual('xxx doc', tasks[0].doc)

