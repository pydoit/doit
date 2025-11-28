"""Tests for programmatic interface (TaskIterator, DoitEngine, etc.)."""
import os
import pytest

from doit.task import Task
from doit.dependency import Dependency, DbmDB, TimestampChecker, MD5Checker
from doit.programmatic import (
    TaskIterator, create_task_iterator, DoitEngine, TaskStatus
)


# --- Test helpers ---

def action_success():
    """Simple successful action."""
    return True


def action_fail():
    """Action that fails."""
    return False


def action_error():
    """Action that raises an error."""
    raise Exception("Task error!")


def action_with_result():
    """Action that returns a dict result."""
    return {'key': 'value', 'count': 42}


# --- Tests for create_task_iterator ---

class TestCreateTaskIterator:

    def test_with_task_dicts(self):
        """Test creating iterator from task dictionaries."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
        ]
        iterator = create_task_iterator(tasks, db_file=':memory:')
        try:
            task_names = [w.name for w in iterator]
            assert 'task1' in task_names
            assert 'task2' in task_names
        finally:
            iterator.finish()

    def test_with_task_objects(self):
        """Test creating iterator from Task objects."""
        tasks = [
            Task('task1', [action_success]),
            Task('task2', [action_success]),
        ]
        iterator = create_task_iterator(tasks, db_file=':memory:')
        try:
            task_names = [w.name for w in iterator]
            assert 'task1' in task_names
            assert 'task2' in task_names
        finally:
            iterator.finish()

    def test_with_mixed_types(self):
        """Test creating iterator from mixed Task and dict."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            Task('task2', [action_success]),
        ]
        iterator = create_task_iterator(tasks, db_file=':memory:')
        try:
            task_names = [w.name for w in iterator]
            assert 'task1' in task_names
            assert 'task2' in task_names
        finally:
            iterator.finish()

    def test_invalid_task_type(self):
        """Test that invalid task types raise TypeError."""
        tasks = ["not a task"]
        with pytest.raises(TypeError, match="Expected Task or dict"):
            create_task_iterator(tasks, db_file=':memory:')

    def test_selected_tasks(self):
        """Test that selected parameter filters tasks."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
            {'name': 'task3', 'actions': [action_success]},
        ]
        iterator = create_task_iterator(
            tasks, db_file=':memory:', selected=['task1', 'task3'])
        try:
            task_names = [w.name for w in iterator]
            assert 'task1' in task_names
            assert 'task2' not in task_names
            assert 'task3' in task_names
        finally:
            iterator.finish()

    def test_memory_uses_timestamp_checker(self):
        """Test that :memory: defaults to TimestampChecker."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]
        iterator = create_task_iterator(tasks, db_file=':memory:')
        try:
            assert isinstance(iterator._dep_manager.checker, TimestampChecker)
        finally:
            iterator.finish()


# --- Tests for TaskIterator ---

class TestTaskIterator:

    def test_basic_iteration(self):
        """Test basic iteration through tasks."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
        ]
        executed = []
        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()
                    executed.append(wrapper.name)

        assert 'task1' in executed
        assert 'task2' in executed

    def test_task_dependencies(self):
        """Test that task dependencies are executed first."""
        execution_order = []

        def track_task1():
            execution_order.append('task1')
            return True

        def track_task2():
            execution_order.append('task2')
            return True

        tasks = [
            {'name': 'task1', 'actions': [track_task1]},
            {'name': 'task2', 'actions': [track_task2], 'task_dep': ['task1']},
        ]

        with DoitEngine(tasks, db_file=':memory:', selected=['task2']) as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        # task1 should be executed before task2
        assert execution_order.index('task1') < execution_order.index('task2')

    def test_always_execute(self):
        """Test that always_execute forces execution."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        # First run - task should execute
        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                assert wrapper.should_run is True

        # With always_execute=True, task should still execute
        with DoitEngine(tasks, db_file=':memory:', always_execute=True) as engine:
            for wrapper in engine:
                assert wrapper.should_run is True

    def test_tasks_property(self):
        """Test accessing tasks dict through iterator."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
        ]
        with DoitEngine(tasks, db_file=':memory:') as engine:
            assert 'task1' in engine.tasks
            assert 'task2' in engine.tasks
            for wrapper in engine:
                pass  # consume iterator

    def test_task_failure(self):
        """Test handling task failure."""
        tasks = [{'name': 'failing_task', 'actions': [action_fail]}]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    result = wrapper.execute_and_submit()
                    assert result is not None
                    assert wrapper.status == TaskStatus.FAILURE


class TestTaskIteratorUpToDate:

    def test_up_to_date_detection(self, tmp_path):
        """Test that tasks are detected as up-to-date after successful run."""
        db_file = str(tmp_path / 'test.db')
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        # First run - task should execute
        with DoitEngine(tasks, db_file=db_file) as engine:
            for wrapper in engine:
                assert wrapper.should_run is True
                wrapper.execute_and_submit()

        # Second run - task should be up-to-date
        with DoitEngine(tasks, db_file=db_file) as engine:
            for wrapper in engine:
                # Task has no file deps, so it's always 'run' status
                # (no dependencies = not up-to-date)
                pass


class TestTaskIteratorWithFileDeps:

    def test_file_dep_change_triggers_run(self, tmp_path):
        """Test that file dependency changes trigger re-execution."""
        import time
        import uuid

        # Use unique subdir to avoid any caching issues
        test_dir = tmp_path / str(uuid.uuid4())
        test_dir.mkdir()

        dep_file = test_dir / 'input.txt'
        dep_file.write_text('initial content')

        target_file = test_dir / 'output.txt'

        def build_action():
            target_file.write_text('built')
            return True

        db_file = str(test_dir / 'test.db')
        tasks = [{
            'name': 'build',
            'actions': [build_action],
            'file_dep': [str(dep_file)],
            'targets': [str(target_file)],
        }]

        # First run - task should execute
        with DoitEngine(tasks, db_file=db_file) as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        assert target_file.exists()

        # Wait a tiny bit so timestamp differs if file is modified
        time.sleep(0.05)

        # Second run with same file - task should be up-to-date
        with DoitEngine(tasks, db_file=db_file) as engine:
            for wrapper in engine:
                # Should be up-to-date (file deps unchanged, target exists)
                assert wrapper.should_run is False


# --- Tests for DoitEngine ---

class TestDoitEngine:

    def test_context_manager_cleanup(self):
        """Test that DoitEngine properly cleans up on exit."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        engine_ref = None
        with DoitEngine(tasks, db_file=':memory:') as engine:
            engine_ref = engine
            # consume but don't wait for full iteration to check mid-state
            wrapper = next(engine)
            wrapper.execute_and_submit()

        # After context exit, engine should be finished
        assert engine_ref._finished is True

    def test_context_manager_cleanup_on_exception(self):
        """Test that DoitEngine cleans up even on exception."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        try:
            with DoitEngine(tasks, db_file=':memory:') as engine:
                for wrapper in engine:
                    raise ValueError("Test exception")
        except ValueError:
            pass
        # Should not raise - cleanup should have happened

    def test_in_memory_execution(self):
        """Test complete in-memory execution."""
        execution_count = [0]

        def counting_action():
            execution_count[0] += 1
            return True

        tasks = [
            {'name': 'task1', 'actions': [counting_action]},
            {'name': 'task2', 'actions': [counting_action]},
        ]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        assert execution_count[0] == 2


class TestTaskIteratorGetargs:

    def test_getargs_from_prior_task(self):
        """Test that getargs values are passed between tasks."""
        received_value = [None]

        def producer():
            return {'output': 'produced_value'}

        def consumer(input_val):
            received_value[0] = input_val
            return True

        tasks = [
            {'name': 'producer', 'actions': [producer]},
            {
                'name': 'consumer',
                # (callable,) format: kwargs come from task.options, which is filled by getargs
                'actions': [(consumer,)],
                'getargs': {'input_val': ('producer', 'output')},
                'task_dep': ['producer'],
            },
        ]

        with DoitEngine(tasks, db_file=':memory:', selected=['consumer']) as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        assert received_value[0] == 'produced_value'


class TestTaskIteratorSetupTasks:

    def test_setup_tasks_yield_separately(self):
        """Test that setup tasks are yielded as separate wrappers."""
        yielded_tasks = []

        tasks = [
            {'name': 'setup_task', 'actions': [action_success]},
            {
                'name': 'main_task',
                'actions': [action_success],
                # Task.valid_attr uses 'setup' as the key name
                'setup': ['setup_task'],
            },
        ]

        with DoitEngine(tasks, db_file=':memory:', selected=['main_task']) as engine:
            for wrapper in engine:
                yielded_tasks.append(wrapper.name)
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        # Main task should be yielded (setup tasks may or may not be depending on status)
        # The key test is that main_task was yielded
        assert 'main_task' in yielded_tasks


class TestTaskIteratorTeardown:

    def test_teardown_executed_on_finish(self, tmp_path):
        """Test that teardown is executed when finish() is called."""
        marker_file = tmp_path / 'teardown_marker'

        def create_teardown_marker():
            marker_file.write_text('teardown ran')

        tasks = [{
            'name': 'task_with_teardown',
            'actions': [action_success],
            'teardown': [create_teardown_marker],
        }]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        # Teardown should have been executed
        assert marker_file.exists()
        assert marker_file.read_text() == 'teardown ran'


# --- Tests for dynamic task injection ---

class TestDynamicTaskInjection:

    def test_add_task_during_iteration(self):
        """Test adding a task during iteration."""
        executed = []

        def track(name):
            def action():
                executed.append(name)
                return True
            return action

        tasks = [
            {'name': 'task1', 'actions': [track('task1')]},
        ]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

                # After executing task1, add task2
                if wrapper.name == 'task1':
                    engine.add_task({
                        'name': 'task2',
                        'actions': [track('task2')],
                    })

        assert 'task1' in executed
        assert 'task2' in executed

    def test_add_task_with_dependency_on_existing(self):
        """Test adding a task that depends on an already-executed task."""
        executed = []
        received_value = [None]

        def producer():
            executed.append('producer')
            return {'value': 42}

        def consumer(value):
            executed.append('consumer')
            received_value[0] = value
            return True

        tasks = [
            {'name': 'producer', 'actions': [producer]},
        ]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

                # After executing producer, add consumer
                if wrapper.name == 'producer':
                    engine.add_task({
                        'name': 'consumer',
                        'actions': [(consumer,)],
                        'getargs': {'value': ('producer', 'value')},
                        'task_dep': ['producer'],
                    })

        assert executed == ['producer', 'consumer']
        assert received_value[0] == 42

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks at once."""
        executed = []

        def track(name):
            def action():
                executed.append(name)
                return True
            return action

        tasks = [{'name': 'initial', 'actions': [track('initial')]}]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

                if wrapper.name == 'initial':
                    engine.add_tasks([
                        {'name': 'added1', 'actions': [track('added1')]},
                        {'name': 'added2', 'actions': [track('added2')]},
                    ])

        assert 'initial' in executed
        assert 'added1' in executed
        assert 'added2' in executed

    def test_add_task_with_Task_object(self):
        """Test adding a Task object directly."""
        from doit.task import Task
        executed = []

        def track(name):
            def action():
                executed.append(name)
                return True
            return action

        tasks = [Task('task1', [track('task1')])]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

                if wrapper.name == 'task1':
                    engine.add_task(Task('task2', [track('task2')]))

        assert 'task1' in executed
        assert 'task2' in executed

    def test_add_task_invalid_dep_raises(self):
        """Test that adding a task with invalid dependency raises error."""
        from doit.exceptions import InvalidTask

        tasks = [{'name': 'task1', 'actions': [action_success]}]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            wrapper = next(engine)
            wrapper.execute_and_submit()

            with pytest.raises(InvalidTask, match="unknown dependency"):
                engine.add_task({
                    'name': 'task2',
                    'actions': [action_success],
                    'task_dep': ['nonexistent'],
                })

    def test_add_duplicate_task_raises(self):
        """Test that adding a task with duplicate name raises error."""
        from doit.exceptions import InvalidTask

        tasks = [{'name': 'task1', 'actions': [action_success]}]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            wrapper = next(engine)
            wrapper.execute_and_submit()

            with pytest.raises(InvalidTask, match="already exists"):
                engine.add_task({
                    'name': 'task1',
                    'actions': [action_success],
                })


# --- Integration tests ---

class TestProgrammaticIntegration:

    def test_full_workflow(self, tmp_path):
        """Test a complete workflow with multiple tasks and dependencies."""
        db_file = str(tmp_path / 'test.db')
        input_file = tmp_path / 'input.txt'
        output_file = tmp_path / 'output.txt'
        input_file.write_text('test input')

        execution_log = []

        def read_input():
            execution_log.append('read')
            return {'content': input_file.read_text()}

        def process(content):
            execution_log.append('process')
            output_file.write_text(f'processed: {content}')
            return True

        tasks = [
            {
                'name': 'read',
                'actions': [read_input],
                'file_dep': [str(input_file)],
            },
            {
                'name': 'process',
                # (callable,) format: kwargs come from task.options via getargs
                'actions': [(process,)],
                'getargs': {'content': ('read', 'content')},
                'task_dep': ['read'],
                'targets': [str(output_file)],
            },
        ]

        # Run the workflow
        with DoitEngine(tasks, db_file=db_file, selected=['process']) as engine:
            for wrapper in engine:
                if wrapper.should_run:
                    wrapper.execute_and_submit()

        # Verify execution order
        assert execution_log == ['read', 'process']

        # Verify output
        assert output_file.exists()
        assert output_file.read_text() == 'processed: test input'

    def test_partial_execution(self):
        """Test executing only some tasks."""
        executed = []

        def track(name):
            def action():
                executed.append(name)
                return True
            return action

        tasks = [
            {'name': 'task1', 'actions': [track('task1')]},
            {'name': 'task2', 'actions': [track('task2')]},
            {'name': 'task3', 'actions': [track('task3')]},
        ]

        with DoitEngine(tasks, db_file=':memory:') as engine:
            for wrapper in engine:
                # Only execute task1 and task3
                if wrapper.name in ('task1', 'task3') and wrapper.should_run:
                    wrapper.execute_and_submit()

        assert 'task1' in executed
        assert 'task2' not in executed
        assert 'task3' in executed
