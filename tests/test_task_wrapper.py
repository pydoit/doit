"""Tests for TaskWrapper class."""
import pytest

from doit.task import Task
from doit.control import ExecNode
from doit.dependency import Dependency, DbmDB
from doit.runner import TaskExecutor
from doit.engine import TaskWrapper, TaskStatus
from doit.exceptions import DependencyError


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


def make_wrapper(task, dep_manager, tasks_dict=None, run_status='run'):
    """Create a TaskWrapper for testing.

    @param task: Task object
    @param dep_manager: Dependency manager
    @param tasks_dict: dict of all tasks (defaults to just this task)
    @param run_status: initial run_status for the node
    """
    if tasks_dict is None:
        tasks_dict = {task.name: task}

    node = ExecNode(task, None)
    node.run_status = run_status

    executor = TaskExecutor(dep_manager)
    return TaskWrapper(node, executor, tasks_dict)


# --- Fixtures ---

@pytest.fixture
def dep_manager(request, tmp_path_factory):
    """Create a dependency manager for tests."""
    filename = str(tmp_path_factory.mktemp('x', True) / 'testdb')
    dep_file = Dependency(DbmDB, filename)

    def cleanup():
        if not dep_file._closed:
            dep_file.close()
    request.addfinalizer(cleanup)

    return dep_file


@pytest.fixture
def memory_dep_manager():
    """Create an in-memory dependency manager for tests."""
    return Dependency(DbmDB, ':memory:')


# --- Test TaskWrapper properties ---

class TestTaskWrapperProperties:

    def test_name(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager)
        assert wrapper.name == "my_task"

    def test_task(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager)
        assert wrapper.task is task

    def test_actions(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager)
        assert len(wrapper.actions) == 1
        # actions are Action objects wrapping the callable
        assert wrapper.actions[0].py_callable is action_success

    def test_should_run_true(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        assert wrapper.should_run is True

    def test_should_run_false_uptodate(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='up-to-date')
        assert wrapper.should_run is False

    def test_should_run_false_ignore(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='ignore')
        assert wrapper.should_run is False

    def test_skip_reason_uptodate(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='up-to-date')
        assert wrapper.skip_reason == 'up-to-date'

    def test_skip_reason_ignore(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='ignore')
        assert wrapper.skip_reason == 'ignore'

    def test_skip_reason_none_when_runnable(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        assert wrapper.skip_reason is None


class TestTaskWrapperStatus:

    def test_status_pending(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status=None)
        assert wrapper.status == TaskStatus.PENDING

    def test_status_ready(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        assert wrapper.status == TaskStatus.READY

    def test_status_skipped_uptodate(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='up-to-date')
        assert wrapper.status == TaskStatus.SKIPPED_UPTODATE

    def test_status_skipped_ignored(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='ignore')
        assert wrapper.status == TaskStatus.SKIPPED_IGNORED

    def test_status_after_execute_before_submit(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        assert wrapper.status == TaskStatus.RUNNING

    def test_status_success_after_submit(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        wrapper.submit()
        assert wrapper.status == TaskStatus.SUCCESS

    def test_status_failure_after_submit(self, dep_manager):
        task = Task("my_task", [action_fail])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        wrapper.submit()
        assert wrapper.status == TaskStatus.FAILURE


# --- Test TaskWrapper.execute() ---

class TestTaskWrapperExecute:

    def test_execute_success(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        result = wrapper.execute()
        assert result is None
        assert wrapper.executed is True
        assert wrapper.result is None

    def test_execute_failure(self, dep_manager):
        task = Task("my_task", [action_fail])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        result = wrapper.execute()
        assert result is not None  # BaseFail
        assert wrapper.executed is True
        assert wrapper.result is not None

    def test_execute_error(self, dep_manager):
        task = Task("my_task", [action_error])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        result = wrapper.execute()
        assert result is not None  # BaseFail
        assert wrapper.executed is True
        assert wrapper.result is not None

    def test_execute_raises_if_already_executed(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        with pytest.raises(RuntimeError, match="already executed"):
            wrapper.execute()

    def test_execute_raises_if_should_not_run(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='up-to-date')
        with pytest.raises(RuntimeError, match="should not run"):
            wrapper.execute()


# --- Test TaskWrapper.submit() ---

class TestTaskWrapperSubmit:

    def test_submit_success(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        success = wrapper.submit()
        assert success is True
        assert wrapper.submitted is True
        # Verify state was saved
        assert dep_manager._in(task.name) is True

    def test_submit_failure(self, dep_manager):
        task = Task("my_task", [action_fail])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        success = wrapper.submit()
        assert success is False
        assert wrapper.submitted is True

    def test_submit_raises_if_already_submitted(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        wrapper.submit()
        with pytest.raises(RuntimeError, match="already submitted"):
            wrapper.submit()

    def test_submit_with_override_result(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        wrapper.execute()
        # Override successful execution with failure
        error = DependencyError("forced failure")
        success = wrapper.submit(result=error)
        assert success is False
        assert wrapper.result is error


# --- Test TaskWrapper.execute_and_submit() ---

class TestTaskWrapperExecuteAndSubmit:

    def test_execute_and_submit_success(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        result = wrapper.execute_and_submit()
        assert result is None
        assert wrapper.executed is True
        assert wrapper.submitted is True
        assert wrapper.status == TaskStatus.SUCCESS

    def test_execute_and_submit_failure(self, dep_manager):
        task = Task("my_task", [action_fail])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        result = wrapper.execute_and_submit()
        assert result is not None
        assert wrapper.executed is True
        assert wrapper.submitted is True
        assert wrapper.status == TaskStatus.FAILURE


# --- Test TaskWrapper with getargs ---

class TestTaskWrapperGetargs:

    def test_getargs_from_completed_task(self, dep_manager):
        """Test that getargs are properly resolved from completed tasks."""
        # Create a "producer" task that has values
        producer = Task("producer", [action_with_result])
        producer.values = {'key': 'producer_value'}

        # Save producer's values to dep_manager
        dep_manager._set(producer.name, '_values_:', producer.values)

        # Create consumer task with getargs
        consumer = Task("consumer", [action_success],
                        getargs={'input': ('producer', 'key')})

        tasks_dict = {producer.name: producer, consumer.name: consumer}
        wrapper = make_wrapper(consumer, dep_manager, tasks_dict, run_status='run')

        # Execute - this should resolve getargs
        wrapper.execute()

        # Verify getargs was resolved
        assert consumer.options.get('input') == 'producer_value'


# --- Test TaskWrapper repr ---

class TestTaskWrapperRepr:

    def test_repr(self, dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, dep_manager, run_status='run')
        assert "my_task" in repr(wrapper)
        assert "ready" in repr(wrapper)


# --- Integration tests with in-memory store ---

class TestTaskWrapperInMemory:
    """Test TaskWrapper with in-memory storage."""

    def test_basic_workflow(self, memory_dep_manager):
        task = Task("my_task", [action_success])
        wrapper = make_wrapper(task, memory_dep_manager, run_status='run')

        assert wrapper.should_run is True
        assert wrapper.status == TaskStatus.READY

        result = wrapper.execute()
        assert result is None
        assert wrapper.status == TaskStatus.RUNNING

        success = wrapper.submit()
        assert success is True
        assert wrapper.status == TaskStatus.SUCCESS

    def test_multiple_tasks(self, memory_dep_manager):
        """Test multiple tasks with dependencies."""
        t1 = Task("task1", [action_success])
        t2 = Task("task2", [action_success], task_dep=['task1'])

        tasks_dict = {t1.name: t1, t2.name: t2}

        # Execute task1
        w1 = make_wrapper(t1, memory_dep_manager, tasks_dict, run_status='run')
        w1.execute_and_submit()
        assert w1.status == TaskStatus.SUCCESS

        # Execute task2
        w2 = make_wrapper(t2, memory_dep_manager, tasks_dict, run_status='run')
        w2.execute_and_submit()
        assert w2.status == TaskStatus.SUCCESS
