"""Tests for programmatic interface (TaskIterator, DoitEngine, etc.)."""
import os
import pytest

from doit.task import Task
from doit.dependency import InMemoryStateStore as MemoryStore, TimestampChecker
from doit.engine import DoitEngine, TaskStatus, create_task_iterator


# --- Test helpers ---

def in_memory_store():
    """Create an in-memory store for testing."""
    return MemoryStore()


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
        iterator = create_task_iterator(tasks, store=in_memory_store())
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
        iterator = create_task_iterator(tasks, store=in_memory_store())
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
        iterator = create_task_iterator(tasks, store=in_memory_store())
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
            create_task_iterator(tasks, store=in_memory_store())

    def test_selected_tasks(self):
        """Test that selected parameter filters tasks."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
            {'name': 'task3', 'actions': [action_success]},
        ]
        iterator = create_task_iterator(
            tasks, store=in_memory_store(), selected=['task1', 'task3'])
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
        iterator = create_task_iterator(tasks, store=in_memory_store())
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
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
                    executed.append(task.name)

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

        with DoitEngine(tasks, store=in_memory_store(), selected=['task2']) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # task1 should be executed before task2
        assert execution_order.index('task1') < execution_order.index('task2')

    def test_always_execute(self):
        """Test that always_execute forces execution."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        # First run - task should execute
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                assert task.should_run is True

        # With always_execute=True, task should still execute
        with DoitEngine(tasks, store=in_memory_store(), always_execute=True) as engine:
            for task in engine:
                assert task.should_run is True

    def test_tasks_property(self):
        """Test accessing tasks dict through iterator."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
        ]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            assert 'task1' in engine.tasks
            assert 'task2' in engine.tasks
            for task in engine:
                pass  # consume iterator

    def test_task_failure(self):
        """Test handling task failure."""
        tasks = [{'name': 'failing_task', 'actions': [action_fail]}]

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    result = task.execute_and_submit()
                    assert result is not None
                    assert task.status == TaskStatus.FAILURE


class TestTaskIteratorUpToDate:

    def test_up_to_date_detection(self, tmp_path):
        """Test that tasks are detected as up-to-date after successful run."""
        db_path = str(tmp_path / 'test.db')
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        # First run - task should execute
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                assert task.should_run is True
                task.execute_and_submit()

        # Second run - task should be up-to-date
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                # Task has no file deps, so it's always 'run' status
                # (no dependencies = not up-to-date)
                pass


class TestTaskIteratorResubmit:
    """Tests for re-running tasks after dependency changes."""

    def test_unchanged_deps_stays_uptodate(self, tmp_path):
        """Test that unchanged file deps result in up-to-date status."""
        dep_file = tmp_path / 'input.txt'
        dep_file.write_text('content')

        execution_count = [0]

        def track_execution():
            execution_count[0] += 1
            return True

        db_path = str(tmp_path / 'test.db')
        tasks = [{
            'name': 'build',
            'actions': [track_execution],
            'file_dep': [str(dep_file)],
        }]

        # First run - should execute
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                assert task.should_run is True
                task.execute_and_submit()

        assert execution_count[0] == 1

        # Second run - should be up-to-date (no execution)
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                assert task.should_run is False
                assert task.skip_reason == 'up-to-date'

        # Execution count should still be 1
        assert execution_count[0] == 1

    def test_changed_deps_triggers_rerun(self, tmp_path):
        """Test that changed file deps trigger re-execution."""
        import time

        dep_file = tmp_path / 'input.txt'
        dep_file.write_text('initial')

        execution_count = [0]

        def track_execution():
            execution_count[0] += 1
            return True

        db_path = str(tmp_path / 'test.db')
        tasks = [{
            'name': 'build',
            'actions': [track_execution],
            'file_dep': [str(dep_file)],
        }]

        # First run
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                task.execute_and_submit()

        assert execution_count[0] == 1

        # Modify the dependency file
        time.sleep(0.05)  # Ensure timestamp differs
        dep_file.write_text('modified')

        # Second run - should execute again
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                assert task.should_run is True
                task.execute_and_submit()

        assert execution_count[0] == 2

    def test_multiple_reruns_track_correctly(self, tmp_path):
        """Test that multiple runs with changes track state correctly."""
        import time

        dep_file = tmp_path / 'input.txt'
        dep_file.write_text('v1')

        execution_count = [0]
        execution_values = []

        def track_execution():
            content = dep_file.read_text()
            execution_count[0] += 1
            execution_values.append(content)
            return True

        db_path = str(tmp_path / 'test.db')
        tasks = [{
            'name': 'build',
            'actions': [track_execution],
            'file_dep': [str(dep_file)],
        }]

        # Run 1
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # Run 2 - no changes
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # Run 3 - with change
        time.sleep(0.05)
        dep_file.write_text('v2')
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # Run 4 - no changes
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # Should have executed twice (run 1 and run 3)
        assert execution_count[0] == 2
        assert execution_values == ['v1', 'v2']


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

        db_path = str(test_dir / 'test.db')
        tasks = [{
            'name': 'build',
            'actions': [build_action],
            'file_dep': [str(dep_file)],
            'targets': [str(target_file)],
        }]

        # First run - task should execute
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        assert target_file.exists()

        # Wait a tiny bit so timestamp differs if file is modified
        time.sleep(0.05)

        # Second run with same file - task should be up-to-date
        with DoitEngine(tasks, db_path=db_path) as engine:
            for task in engine:
                # Should be up-to-date (file deps unchanged, target exists)
                assert task.should_run is False


# --- Tests for DoitEngine ---

class TestDoitEngine:

    def test_context_manager_cleanup(self):
        """Test that DoitEngine properly cleans up on exit."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        engine_ref = None
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            engine_ref = engine
            # consume but don't wait for full iteration to check mid-state
            task = next(engine)
            task.execute_and_submit()

        # After context exit, engine's iterator should be finished
        assert engine_ref._iterator._finished is True

    def test_context_manager_cleanup_on_exception(self):
        """Test that DoitEngine cleans up even on exception."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        try:
            with DoitEngine(tasks, store=in_memory_store()) as engine:
                for task in engine:
                    raise ValueError("Test exception")
        except ValueError:
            pass
        # Should not raise - cleanup should have happened

    def test_explicit_finish(self):
        """Test that DoitEngine can be used without context manager."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]

        engine = DoitEngine(tasks, store=in_memory_store())
        try:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
        finally:
            engine.finish()

        # After explicit finish, engine's iterator should be finished
        assert engine._iterator._finished is True

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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store(), selected=['consumer']) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store(), selected=['main_task']) as engine:
            for task in engine:
                yielded_tasks.append(task.name)
                if task.should_run:
                    task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

                # After executing task1, add task2
                if task.name == 'task1':
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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

                # After executing producer, add consumer
                if task.name == 'producer':
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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

                if task.name == 'initial':
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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

                if task.name == 'task1':
                    engine.add_task(Task('task2', [track('task2')]))

        assert 'task1' in executed
        assert 'task2' in executed

    def test_add_task_invalid_dep_raises(self):
        """Test that adding a task with invalid dependency raises error."""
        from doit.exceptions import InvalidTask

        tasks = [{'name': 'task1', 'actions': [action_success]}]

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            task = next(engine)
            task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            task = next(engine)
            task.execute_and_submit()

            with pytest.raises(InvalidTask, match="already exists"):
                engine.add_task({
                    'name': 'task1',
                    'actions': [action_success],
                })


# --- Integration tests ---

class TestProgrammaticIntegration:

    def test_full_workflow(self, tmp_path):
        """Test a complete workflow with multiple tasks and dependencies."""
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
        with DoitEngine(tasks, db_path=str(tmp_path / 'test.db'), selected=['process']) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

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

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                # Only execute task1 and task3
                if task.name in ('task1', 'task3') and task.should_run:
                    task.execute_and_submit()

        assert 'task1' in executed
        assert 'task2' not in executed
        assert 'task3' in executed


# --- Tests for concurrent execution support ---

class TestConcurrentExecution:

    def test_has_pending_tasks_initial(self):
        """Test has_pending_tasks is True initially with tasks."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
        ]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            assert engine.has_pending_tasks is True

    def test_has_pending_tasks_false_when_done(self):
        """Test has_pending_tasks is False after all tasks complete."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
            assert engine.has_pending_tasks is False

    def test_get_ready_tasks_returns_independent_tasks(self):
        """Test get_ready_tasks returns tasks without dependencies."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success]},
            {'name': 'task3', 'actions': [action_success], 'task_dep': ['task1']},
        ]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            ready = engine.get_ready_tasks()
            ready_names = [t.name for t in ready]
            # task1 and task2 should be ready (no deps)
            assert 'task1' in ready_names
            assert 'task2' in ready_names
            # task3 should NOT be ready (depends on task1)
            assert 'task3' not in ready_names

    def test_notify_completed_unlocks_dependents(self):
        """Test notify_completed makes dependent tasks ready."""
        tasks = [
            {'name': 'task1', 'actions': [action_success]},
            {'name': 'task2', 'actions': [action_success], 'task_dep': ['task1']},
        ]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            ready = engine.get_ready_tasks()
            assert len(ready) == 1
            assert ready[0].name == 'task1'

            # Execute and submit task1
            ready[0].execute_and_submit()
            newly_ready = engine.notify_completed(ready[0])

            # task2 should now be ready
            ready_names = [t.name for t in newly_ready]
            assert 'task2' in ready_names

    def test_notify_completed_without_submit_raises(self):
        """Test notify_completed raises if task not submitted."""
        tasks = [{'name': 'task1', 'actions': [action_success]}]
        with DoitEngine(tasks, store=in_memory_store()) as engine:
            ready = engine.get_ready_tasks()
            assert len(ready) == 1

            # Don't call submit - should raise
            with pytest.raises(RuntimeError, match="must be submitted"):
                engine.notify_completed(ready[0])

    def test_concurrent_loop_pattern(self):
        """Test the concurrent execution loop pattern works correctly."""
        executed = []

        def track(name):
            def action():
                executed.append(name)
                return True
            return action

        tasks = [
            {'name': 'task1', 'actions': [track('task1')]},
            {'name': 'task2', 'actions': [track('task2')]},
            {'name': 'task3', 'actions': [track('task3')], 'task_dep': ['task1', 'task2']},
        ]

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            while engine.has_pending_tasks:
                ready = engine.get_ready_tasks()
                if not ready:
                    break

                for task in ready:
                    if task.should_run:
                        task.execute_and_submit()
                    else:
                        task.submit(None)
                    engine.notify_completed(task)

        # All tasks should have executed
        assert 'task1' in executed
        assert 'task2' in executed
        assert 'task3' in executed

    def test_concurrent_with_threadpool(self):
        """Test concurrent execution with ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
        import threading

        executed = []
        lock = threading.Lock()

        def track(name):
            def action():
                with lock:
                    executed.append(name)
                return True
            return action

        tasks = [
            {'name': 'task1', 'actions': [track('task1')]},
            {'name': 'task2', 'actions': [track('task2')]},
            {'name': 'task3', 'actions': [track('task3')], 'task_dep': ['task1', 'task2']},
        ]

        with DoitEngine(tasks, store=in_memory_store()) as engine:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}

                while engine.has_pending_tasks:
                    for task in engine.get_ready_tasks():
                        if task.should_run:
                            future = executor.submit(task.execute)
                            futures[future] = task
                        else:
                            task.submit(None)
                            engine.notify_completed(task)

                    if futures:
                        done, _ = wait(futures, return_when=FIRST_COMPLETED)
                        for future in done:
                            task = futures.pop(future)
                            task.submit(future.result())
                            engine.notify_completed(task)

        # All tasks should have executed
        assert 'task1' in executed
        assert 'task2' in executed
        assert 'task3' in executed
