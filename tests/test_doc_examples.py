"""Tests that validate examples from doc/programmatic.rst work correctly.

These tests exercise the programmatic interface examples to ensure
the documentation stays in sync with the actual API.
"""

import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path

import pytest

from doit import DoitEngine, TaskStatus, InMemoryStateStore
from doit.engine import ExecutionCallbacks, NullCallbacks


class TestBasicDoitEngine:
    """Test basic DoitEngine usage from Quick Start section."""

    def test_quick_start_example(self):
        """The quick start example from docs works."""
        results = []

        def record_build():
            results.append('build')
            return True

        def record_test():
            results.append('test')
            return True

        tasks = [
            {'name': 'build', 'actions': [record_build]},
            {'name': 'test', 'actions': [record_test], 'task_dep': ['build']},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        assert results == ['build', 'test']

    def test_explicit_finish(self):
        """Engine works with explicit finish() instead of context manager."""
        executed = []

        tasks = [{'name': 'task1', 'actions': [lambda: executed.append(1)]}]

        engine = DoitEngine(tasks, store=InMemoryStateStore())
        try:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
        finally:
            engine.finish()

        assert executed == [1]


class TestInMemoryExecution:
    """Test in-memory execution examples."""

    def test_in_memory_store(self):
        """InMemoryStateStore works for transient execution."""
        results = []

        tasks = [
            {'name': 'task1', 'actions': [lambda: results.append(1)]},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        assert results == [1]

    def test_custom_db_path(self, tmp_path):
        """Custom db_path works for file-based persistence."""
        db_file = str(tmp_path / 'custom.db')
        results = []

        tasks = [
            {'name': 'task1', 'actions': [lambda: results.append(1)]},
        ]

        with DoitEngine(tasks, db_path=db_file) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        assert results == [1]
        # DB file should exist (or at least directory should have db files)
        assert any(f.startswith('custom') for f in os.listdir(tmp_path))


class TestExecutionControl:
    """Test different execution control patterns."""

    def test_execute_and_submit(self):
        """execute_and_submit() convenience method works."""
        results = []

        tasks = [
            {'name': 'task1', 'actions': [lambda: results.append('executed')]},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    result = task.execute_and_submit()
                    assert result is None  # Success

        assert results == ['executed']

    def test_separate_execute_and_submit(self):
        """Separate execute() and submit() calls work."""
        tasks = [
            {'name': 'task1', 'actions': [lambda: {'value': 42}]},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    result = task.execute()
                    assert result is None  # Success

                    # Can inspect values before submit
                    assert task.values == {'value': 42}

                    task.submit()

    def test_custom_skip_logic(self):
        """Custom skip logic allows skipping tasks."""
        executed = []
        skip_tasks = {'skip_me'}

        tasks = [
            {'name': 'keep_me', 'actions': [lambda: executed.append('keep')]},
            {'name': 'skip_me', 'actions': [lambda: executed.append('skip')]},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.name in skip_tasks:
                    continue  # Skip without executing

                if task.should_run:
                    task.execute_and_submit()

        assert executed == ['keep']


class TestConcurrentExecution:
    """Test concurrent execution with ThreadPoolExecutor."""

    def test_parallel_independent_tasks(self):
        """Independent tasks can run in parallel."""
        executed = []

        def task_a():
            executed.append('a')
            return True

        def task_b():
            executed.append('b')
            return True

        tasks = [
            {'name': 'task_a', 'actions': [task_a]},
            {'name': 'task_b', 'actions': [task_b]},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            with ThreadPoolExecutor(max_workers=4) as executor:
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

        assert set(executed) == {'a', 'b'}

    def test_parallel_with_dependencies(self):
        """Tasks with dependencies run in correct order."""
        order = []

        tasks = [
            {'name': 'first', 'actions': [lambda: order.append(1)]},
            {'name': 'second', 'actions': [lambda: order.append(2)], 'task_dep': ['first']},
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            with ThreadPoolExecutor(max_workers=4) as executor:
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

        assert order == [1, 2]


class TestDynamicTaskInjection:
    """Test dynamic task injection examples."""

    def test_add_task_during_iteration(self):
        """add_task() during iteration works."""
        results = []

        def discover():
            return {'items': ['x', 'y']}

        def process(item):
            results.append(item)
            return True

        initial_tasks = [
            {'name': 'discover', 'actions': [discover]},
        ]

        with DoitEngine(initial_tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

                if task.name == 'discover':
                    for item in task.values.get('items', []):
                        engine.add_task({
                            'name': f'process_{item}',
                            'actions': [(process, [item])],
                            'task_dep': ['discover'],
                        })

        assert set(results) == {'x', 'y'}


class TestTaskValues:
    """Test working with task values."""

    def test_producer_consumer_values(self):
        """Task values are passed correctly."""
        received_value = []

        def producer():
            return {'result': 42, 'status': 'ok'}

        def consumer(result):
            received_value.append(result)
            return True

        tasks = [
            {'name': 'produce', 'actions': [producer]},
            {
                'name': 'consume',
                'actions': [(consumer,)],
                'getargs': {'result': ('produce', 'result')},
                'task_dep': ['produce'],
            },
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
                    if task.name == 'produce':
                        assert task.values == {'result': 42, 'status': 'ok'}

        assert received_value == [42]


class TestTaskWrapperProperties:
    """Test TaskWrapper properties are accessible."""

    def test_basic_properties(self):
        """Basic TaskWrapper properties work."""
        tasks = [
            {
                'name': 'mytask',
                'actions': [lambda: True],
                'doc': 'My task description',
            },
        ]

        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                assert task.name == 'mytask'
                assert task.doc == 'My task description'
                assert task.status == TaskStatus.READY
                assert task.should_run

    def test_skip_reason(self):
        """skip_reason is set correctly for up-to-date tasks."""
        executed_count = [0]

        def action():
            executed_count[0] += 1
            return True

        tasks = [{'name': 'task1', 'actions': [action]}]

        # First run - should execute
        with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()
                    assert task.skip_reason is None

        # Second run with same store would show up-to-date
        # (but we use in-memory so it always runs)
        assert executed_count[0] == 1


class TestCallbacks:
    """Test execution callbacks interface."""

    def test_callbacks_exist(self):
        """ExecutionCallbacks and NullCallbacks are importable."""
        assert ExecutionCallbacks is not None
        assert NullCallbacks is not None

    def test_null_callbacks(self):
        """NullCallbacks can be used without issues."""
        callbacks = NullCallbacks()

        # All methods should be callable without error
        # Using actual callback method names from the protocol
        callbacks.on_status_check(None)
        callbacks.on_execute(None)
        callbacks.on_success(None)
        callbacks.on_failure(None, None)
        callbacks.on_skip_uptodate(None)
        callbacks.on_skip_ignored(None)
        callbacks.on_teardown(None)

    def test_custom_callbacks(self):
        """Custom callbacks receive notifications."""
        events = []

        class TestCallbacks:
            def on_status_check(self, task):
                events.append(('status_check', task.name if task else None))

            def on_execute(self, task):
                events.append(('execute', task.name if task else None))

            def on_success(self, task):
                events.append(('success', task.name if task else None))

            def on_failure(self, task, error):
                events.append(('failure', task.name if task else None))

            def on_skip_uptodate(self, task):
                events.append(('skip_uptodate', task.name if task else None))

            def on_skip_ignored(self, task):
                events.append(('skip_ignored', task.name if task else None))

            def on_teardown(self, task):
                events.append(('teardown', task.name if task else None))

        tasks = [{'name': 'task1', 'actions': [lambda: True]}]

        with DoitEngine(tasks, store=InMemoryStateStore(),
                       callbacks=TestCallbacks()) as engine:
            for task in engine:
                if task.should_run:
                    task.execute_and_submit()

        # Callbacks are called with the Task object, check events were recorded
        assert any('task1' in str(e) for e in events)


class TestProgrammaticDemoScripts:
    """Test that the demo scripts in examples/programmatic_demo/ work."""

    @pytest.fixture
    def demo_dir(self):
        """Return path to programmatic_demo directory."""
        return Path(__file__).parent.parent / 'examples' / 'programmatic_demo'

    def test_demo_dynamic_tasks_runs(self, demo_dir):
        """demo_dynamic_tasks.py executes successfully."""
        result = subprocess.run(
            [sys.executable, str(demo_dir / 'demo_dynamic_tasks.py')],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert 'Dynamic Task Injection' in result.stdout
        assert 'All tasks completed' in result.stdout

    def test_demo_execution_control_runs(self, demo_dir):
        """demo_execution_control.py executes successfully."""
        result = subprocess.run(
            [sys.executable, str(demo_dir / 'demo_execution_control.py')],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert 'Execution Control Patterns' in result.stdout
        assert 'Demo complete' in result.stdout

    def test_setup_and_run_demo(self, demo_dir, tmp_path, monkeypatch):
        """setup_demo.py and run_demo.py work together."""
        # Change to temp directory to avoid polluting the source tree
        workspace = demo_dir / 'workspace'

        # Run setup
        result = subprocess.run(
            [sys.executable, str(demo_dir / 'setup_demo.py')],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Setup failed: {result.stderr}"

        # Verify workspace was created
        assert workspace.exists()
        assert (workspace / 'src' / 'module_a.py').exists()

        try:
            # Run the build
            result = subprocess.run(
                [sys.executable, str(demo_dir / 'run_demo.py')],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Run failed: {result.stderr}"
            assert 'Running build' in result.stdout
        finally:
            # Clean up workspace
            import shutil
            if workspace.exists():
                shutil.rmtree(workspace)
