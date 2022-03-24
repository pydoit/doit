import os
import inspect
from operator import attrgetter

import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, DelayedLoader, Task
from doit.loader import flat_generator, get_module
from doit.loader import load_tasks, load_doit_config, generate_tasks
from doit.loader import create_after, task_params


class TestFlatGenerator(object):
    def test_nested(self):
        def myg(items):
            for x in items:
                yield x
        flat = flat_generator(myg([1, myg([2, myg([3, myg([4, myg([5])])])])]))
        assert [1,2,3,4,5] == [f[0] for f in flat]


class TestGetModule(object):
    def testAbsolutePath(self, restore_cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        assert hasattr(dodo_module, 'task_xxx1')

    def testRelativePath(self, restore_cwd):
        # test relative import but test should still work from any path
        # so change cwd.
        this_path = os.path.join(os.path.dirname(__file__),'..')
        os.chdir(os.path.abspath(this_path))
        fileName = "tests/loader_sample.py"
        dodo_module = get_module(fileName)
        assert hasattr(dodo_module, 'task_xxx1')

    def testWrongFileName(self):
        fileName = os.path.join(os.path.dirname(__file__),"i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName)

    def testInParentDir(self, restore_cwd):
        os.chdir(os.path.join(os.path.dirname(__file__), "data"))
        fileName = "loader_sample.py"
        pytest.raises(InvalidDodoFile, get_module, fileName)
        get_module(fileName, seek_parent=True)
        # cwd is changed to location of dodo.py
        assert os.getcwd() == os.path.dirname(os.path.abspath(fileName))

    def testWrongFileNameInParentDir(self, restore_cwd):
        os.chdir(os.path.join(os.path.dirname(__file__), "data"))
        fileName = os.path.join("i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName, seek_parent=True)

    def testInvalidCwd(self, restore_cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "dataX")
        pytest.raises(InvalidCommand, get_module, fileName, cwd)


class TestLoadTasks(object):

    @pytest.fixture
    def dodo(self):
        def task_xxx1():
            """task doc"""
            return {'actions':['do nothing']}

        def task_yyy2():
            return {'actions':None}

        def task_meta():
            return {
                'actions' : ['do nothing'],
                'meta'    : { 'a' : ['b', 'c']},
            }

        def bad_seed(): pass
        task_nono = 5
        task_nono # pyflakes
        return locals()

    def testNormalCase(self, dodo):
        task_list = load_tasks(dodo)
        assert 3 == len(task_list)
        assert 'xxx1' == task_list[0].name
        assert 'yyy2' == task_list[1].name
        assert 'meta' == task_list[2].name

    def testCreateAfterDecorator(self):
        @create_after('yyy2')
        def task_zzz3(): # pragma: no cover
            pass

        # create_after annotates the function
        assert isinstance(task_zzz3.doit_create_after, DelayedLoader)
        assert task_zzz3.doit_create_after.task_dep == 'yyy2'

    def testInitialLoadDelayedTask(self, dodo):
        @create_after('yyy2')
        def task_zzz3(): # pragma: no cover
            raise Exception('Cant be executed on load phase')
        dodo['task_zzz3'] = task_zzz3

        # placeholder task is created with `loader` attribute
        task_list = load_tasks(dodo, allow_delayed=True)
        z_task = [t for t in task_list if t.name=='zzz3'][0]
        assert z_task.loader.task_dep == 'yyy2'
        assert z_task.loader.creator == task_zzz3

    def testInitialLoadDelayedTask_no_delayed(self, dodo):
        @create_after('yyy2')
        def task_zzz3():
            yield {'basename': 'foo', 'actions': None}
            yield {'basename': 'bar', 'actions': None}
        dodo['task_zzz3'] = task_zzz3

        # load tasks as done by the `list` command
        task_list = load_tasks(dodo, allow_delayed=False)
        tasks = {t.name:t for t in task_list}
        assert 'zzz3' not in tasks
        assert tasks['foo'].loader is None
        assert tasks['bar'].loader is None

    def testInitialLoadDelayedTask_creates(self, dodo):
        @create_after('yyy2', creates=['foo', 'bar'])
        def task_zzz3(): # pragma: no cover
            '''not loaded task doc'''
            raise Exception('Cant be executed on load phase')
        dodo['task_zzz3'] = task_zzz3

        # placeholder task is created with `loader` attribute
        task_list = load_tasks(dodo, allow_delayed=True)
        tasks = {t.name:t for t in task_list}
        assert 'zzz3' not in tasks
        f_task = tasks['foo']
        assert f_task.loader.task_dep == 'yyy2'
        assert f_task.loader.creator == task_zzz3
        assert tasks['bar'].loader.task_dep == tasks['foo'].loader.task_dep
        assert tasks['foo'].doc == 'not loaded task doc'

        # make sure doit can be executed more then once in single process GH#381
        list2 = load_tasks(dodo, allow_delayed=True)
        tasks2 = {t.name:t for t in list2}
        assert tasks['bar'].loader is not tasks2['bar'].loader

    def testCreateAfterDecoratorOnMethod(self):
        'Check that class-defined tasks are loaded as bound methods'
        class Tasks:
            @create_after('yyy2')
            def task_zzz3(): # pragma: no cover
                pass

        # create_after annotates the function
        task_list = load_tasks({'task_zzz3': Tasks().task_zzz3}, allow_delayed=True)
        tasks = {t.name:t for t in task_list}
        task_zzz3 = tasks['zzz3']
        assert isinstance(task_zzz3.loader, DelayedLoader)
        # check creator is a bound method, not a plain function
        assert getattr(task_zzz3.loader.creator, '__self__', None) is not None

    def testCreateAfterDecoratorOnMethodWithParams(self, dodo):
        'Check that class-defined tasks support the creates argument of @create_after'
        class Tasks:
            @create_after('yyy2', creates=['foo', 'bar'])
            def task_zzz3(): # pragma: no cover
                '''not loaded task doc'''
                raise Exception('Cant be executed on load phase')

        # placeholder task is created with `loader` attribute
        task_list = load_tasks({'task_zzz3': Tasks().task_zzz3}, allow_delayed=True)
        tasks = {t.name:t for t in task_list}
        assert 'zzz3' not in tasks
        f_task = tasks['foo']
        assert f_task.loader.task_dep == 'yyy2'
        assert getattr(f_task.loader.creator, '__self__', None) is not None
        # loaders are not the same because of #381 (multiple execution on same process)
        # But this is not a problem because once the task already exists, the loader is just not used.
        # assert tasks['bar'].loader is tasks['foo'].loader
        assert tasks['foo'].doc == 'not loaded task doc'

    def testNameInBlacklist(self):
        dodo_module = {'task_cmd_name': lambda:None}
        pytest.raises(InvalidDodoFile, load_tasks, dodo_module, ['cmd_name'])

    def testDocString(self, dodo):
        task_list = load_tasks(dodo)
        assert "task doc" == task_list[0].doc

    def testMetaInfo(self, dodo):
        task_list = load_tasks(dodo)
        assert task_list[2].meta == {'a': ['b', 'c']}

    def testUse_create_doit_tasks(self):
        def original(): pass
        def creator():
            return {'actions': ['do nothing'], 'file_dep': ['foox']}
        original.create_doit_tasks = creator
        task_list = load_tasks({'x': original})
        assert 1 == len(task_list)
        assert set(['foox']) == task_list[0].file_dep

    def testUse_create_doit_tasks_class_method(self):
        class Foo(object):
            def __init__(self):
                self.create_doit_tasks = self._create_doit_tasks
            def _create_doit_tasks(self):
                return {'actions': ['do nothing'], 'file_dep': ['fooy']}

        task_list = load_tasks({'Foo':Foo, 'foo':Foo()})
        assert len(task_list) == 1
        assert task_list[0].file_dep == set(['fooy'])

    def testUse_create_doit_tasks_basename_kwargs(self):
        class Foo(object):
            def __init__(self):
                @task_params([{"name": "t", "default": None, "type": list}])
                def creator(**kwargs):
                    return self._create_doit_tasks(**kwargs)
                creator.basename = 'my-foo'
                self.create_doit_tasks = creator

            def _create_doit_tasks(self, **kwargs):
                return {'actions': ['do nothing'], 'file_dep': ['fooy'], 'targets': kwargs['t']}

        task_list = load_tasks({'Foo':Foo, 'foo':Foo()}, task_opts={'my-foo': {'t': ['bar']}})
        assert len(task_list) == 1
        assert task_list[0].name == 'my-foo'
        assert task_list[0].targets == ['bar']

    def testUse_object_methods(self):
        class Dodo(object):
            def foo(self): # pragma: no cover
                pass

            def task_method1(self):
                return {'actions':None}

            def task_method2(self):
                return {'actions':None}

        methods = dict(inspect.getmembers(Dodo()))
        task_list = load_tasks(methods)
        assert 2 == len(task_list)
        assert 'method1' == task_list[0].name
        assert 'method2' == task_list[1].name



class TestTaskGeneratorParams(object):

    def test_task_params_annotations(self):
        params = [{"name": "foo", "default": "bar", "long": "foo"}]
        func = task_params(params)(lambda: 1)
        assert func._task_creator_params == params

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
        assert task.doc == 'bar'
        task.init_options()
        assert task.options['foo'] == 'bar'

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
        assert task.doc == 'from_arg'


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
        task_list = load_tasks({'task_foo': task_foo}, args=args, task_opts=task_opts)
        task = task_list.pop()
        assert task.doc == 'from_api'


    def test_args_second(self):
        def task_bar():
            return {'actions': []}

        @task_params([{"name": "foo", "default": "placeholder", "long": "foo"}])
        def task_foo(foo):
            return {
                'actions': [],
                'doc': foo
            }
        args = ['bar', 'foo', '--foo=from_arg']
        task_list = load_tasks({'task_foo': task_foo, 'task_bar': task_bar}, args=args)
        assert len(task_list) == 2
        bar, foo = sorted(task_list, key=attrgetter('name'))
        assert foo.name == 'foo'
        assert foo.doc == 'from_arg'


    def test_config(self):
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        config = {'task:foo': {'fp': 'from_config'}}
        task_list = load_tasks({'task_foo': task_foo}, args=(), config=config)
        task = task_list.pop()
        assert task.doc == 'from_config'
        # config is overwritten from args
        args = ['foo', '--fp=from_arg']
        task_list2 = load_tasks({'task_foo': task_foo}, args=args, config=config)
        task2 = task_list2.pop()
        assert task2.doc == 'from_arg'


    def test_method(self):
        'Ensure that a task parameter can be passed to the task generator defined as a class method.'
        class Tasks(object):
            @task_params([{"name": "param1", "default": "placeholder", "long": "param1"}])
            def task_foo(self, param1):
                for i in range(2):
                    yield {
                        'name': 'subtask' + str(i),
                        'actions': [],
                        'doc': param1,
                    }

        foo = Tasks().task_foo
        task_list = load_tasks({'task_foo': foo}, args=('foo', '--param1=my_val'))

        assert len(task_list) == 3
        tasks = {t.name: t for t in task_list}

        assert len(tasks['foo'].params) == 0
        assert len(tasks['foo'].creator_params) == 1
        assert tasks['foo'].doc == ''

        assert len(tasks['foo:subtask0'].params) == 0
        assert tasks['foo:subtask0'].doc == 'my_val'


    def test_delayed(self):
        @create_after()
        @task_params([{"name": "fp", "default": "default p", "long": "fp"}])
        def task_foo(fp):
            return {
                'actions': [],
                'doc': fp
            }
        args = ['foo', '--fp=from_arg']
        task_list = load_tasks({'task_foo': task_foo}, allow_delayed=True, args=args)
        task = task_list.pop()
        assert task.name == 'foo'
        assert task.loader.kwargs == {'fp': 'from_arg'}
        assert len(task.creator_params) == 1


    def test_dup_param(self):
        'Ensure that `params` field and @task_params definitions are prohibited'
        @task_params([{"name": "foo", "default": "decorator", "long": "foo"}])
        def task_dup(foo):
            return {
                'actions': [],
                'params': [{"name": "bar", "default": "dict", "long": "bar"}],
            }

        with pytest.raises(InvalidTask) as exc_info:
            load_tasks({'task_dup': task_dup})
        assert ('attribute can not be used in conjuction with' in str(exc_info.value))




class TestDodoConfig(object):

    def testConfigType_Error(self):
        pytest.raises(InvalidDodoFile, load_doit_config, {'DOIT_CONFIG': 'abc'})

    def testConfigDict_Ok(self,):
        config = load_doit_config({'DOIT_CONFIG': {'verbose': 2}})
        assert {'verbose': 2} == config

    def testDefaultConfig_Dict(self):
        config = load_doit_config({'whatever': 2})
        assert {} == config



class TestGenerateTaskInvalid(object):
    def testInvalidValue(self):
        pytest.raises(InvalidTask, generate_tasks, "dict",'xpto 14')

class TestGenerateTaskNone(object):
    def testEmpty(self):
        tasks = generate_tasks('xx', None)
        assert len(tasks) == 0


class TestGenerateTasksSingle(object):
    def testDict(self):
        tasks = generate_tasks("my_name", {'actions':['xpto 14']})
        assert isinstance(tasks[0], Task)
        assert "my_name" == tasks[0].name

    def testTaskObj(self):
        tasks = generate_tasks("foo", Task('bar', None))
        assert 1 == len(tasks)
        assert tasks[0].name == 'bar'

    def testBaseName(self):
        tasks = generate_tasks("function_name", {
                'basename': 'real_task_name',
                'actions':['xpto 14']
                })
        assert isinstance(tasks[0], Task)
        assert "real_task_name" == tasks[0].name

    # name field is only for subtasks.
    def testInvalidNameField(self):
        pytest.raises(InvalidTask, generate_tasks, "my_name",
                                 {'actions':['xpto 14'],'name':'bla bla'})


    def testUseDocstring(self):
        tasks = generate_tasks("dict",{'actions':['xpto 14']}, "my doc")
        assert "my doc" == tasks[0].doc

    def testDocstringNotUsed(self):
        mytask = {'actions':['xpto 14'], 'doc':'from dict'}
        tasks = generate_tasks("dict", mytask, "from docstring")
        assert "from dict" == tasks[0].doc


class TestGenerateTasksGenerator(object):

    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = generate_tasks("xpto", f_xpto())
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert tasks[0].subtask_of is None
        assert "xpto:0" == tasks[0].task_dep[0]
        assert "xpto:0" == tasks[1].name
        assert tasks[1].subtask_of == 'xpto'

    def testMultiLevelGenerator(self):
        def f_xpto(base_name):
            """second level docstring"""
            for i in range(3):
                name = "%s-%d" % (base_name, i)
                yield {'name':name, 'actions' :["xpto -%d"%i]}
        def f_first_level():
            for i in range(2):
                yield f_xpto(str(i))
        tasks = generate_tasks("xpto", f_first_level())
        assert isinstance(tasks[0], Task)
        assert 7 == len(tasks)
        assert tasks[0].subtask_of is None
        assert f_xpto.__doc__ == tasks[0].doc
        assert tasks[1].subtask_of == 'xpto'
        assert "xpto:0-0" == tasks[1].name
        assert "xpto:1-2" == tasks[-1].name


    def testGeneratorReturnTaskObj(self):
        def foo(base_name):
            for i in range(3):
                name = "%s-%d" % (base_name, i)
                yield Task(name, actions=["xpto -%d"%i])
        tasks = generate_tasks("foo", foo('bar'))
        assert 3 == len(tasks)
        assert tasks[0].name == 'bar-0'
        assert tasks[1].name == 'bar-1'
        assert tasks[2].name == 'bar-2'


    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d" % i
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())


    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions' :["xpto -%d"%i]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasename(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':str(i), 'actions' :["xpto"]}
        tasks = sorted(generate_tasks("xpto", f_xpto()), key=lambda t:t.name)
        assert isinstance(tasks[0], Task)
        assert 3 == len(tasks)
        assert "0" == tasks[0].name
        assert tasks[0].subtask_of is None
        assert tasks[1].subtask_of is None

    def testGeneratorBasenameName(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':'xpto', 'name':str(i), 'actions' :["a"]}
        tasks = sorted(generate_tasks("f_xpto", f_xpto()))
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert "xpto" == tasks[0].name
        assert "xpto:0" == tasks[1].name
        assert tasks[0].subtask_of is None
        assert tasks[1].subtask_of == 'xpto'

    def testGeneratorBasenameCanNotRepeat(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':'again', 'actions' :["xpto"]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasenameCanNotRepeatNonGroup(self):
        def f_xpto():
            yield {'basename': 'xpto', 'actions':["a"]}
            for i in range(3):
                yield {'name': str(i),
                       'actions' :["a"]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorNameCanNotRepeat(self):
        def f_xpto():
            yield {'basename':'bn', 'name': 'xxx', 'actions' :["xpto"]}
            yield {'basename':'bn', 'name': 'xxx', 'actions' :["xpto2"]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDocString(self):
        def f_xpto():
            "the doc"
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = sorted(generate_tasks("xpto", f_xpto(), f_xpto.__doc__))
        assert "the doc" == tasks[0].doc

    def testGeneratorWithNoTasks(self):
        def f_xpto():
            for x in []: yield x
        tasks = generate_tasks("xpto", f_xpto())
        assert 1 == len(tasks)
        assert "xpto" == tasks[0].name
        assert tasks[0].subtask_of is None


    def testGeneratorBaseOnly(self):
        def f_xpto():
            yield {'basename':'xpto', 'name':None, 'doc': 'xxx doc'}
        tasks = sorted(generate_tasks("f_xpto", f_xpto()))
        assert 1 == len(tasks)
        assert isinstance(tasks[0], Task)
        assert "xpto" == tasks[0].name
        assert tasks[0].has_subtask
        assert 'xxx doc' == tasks[0].doc
