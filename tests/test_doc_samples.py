"""Tests that validate all doc/samples/*.py files are valid dodo files.

These tests ensure all sample dodo files in the documentation can be
successfully loaded by doit's task loader.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from doit.cmd.base import Command, ModuleTaskLoader
from doit.loader import flat_generator


# Get all sample files
SAMPLES_DIR = Path(__file__).parent.parent / 'doc' / 'samples'
SAMPLE_FILES = sorted(SAMPLES_DIR.glob('*.py'))

# Files that require special handling or should be skipped
SKIP_SAMPLES = {
    # These samples need external files or dependencies
    'compile.py',           # Needs .c files
    'compile_pathlib.py',   # Needs .c files
    'cproject.py',          # Needs C project files
    'download.py',          # Requires network access
    'longrunning.py',       # Designed for long-running demo
    'settrace.py',          # Uses strace (Linux only)
    'initial_workdir.py',   # Changes working directory
    'custom_cmd.py',        # Defines command, not tasks
    'module_loader.py',     # Loader script, not dodo
    'custom_loader.py',     # Loader class, not dodo
    'my_dodo.py',           # Example dodo, uses external my_tasks
    'tar.py',               # Creates tar files
    'import_tasks.py',      # Imports from my_tasks.py
    'touch.py',             # Uses touch tool on files
    # My_* files are supporting modules, not dodo files
    'my_module_with_tasks.py',
    'my_tasks.py',
}


def get_module_from_path(filepath):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location("sample_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sample_module"] = module
    spec.loader.exec_module(module)
    return module


def find_task_creators(module):
    """Find all task_* functions in a module."""
    creators = []
    for name in dir(module):
        if name.startswith('task_'):
            obj = getattr(module, name)
            if callable(obj):
                creators.append((name, obj))
    return creators


class TestDocSamplesLoad:
    """Test that doc/samples files can be loaded."""

    @pytest.fixture
    def sample_files(self):
        """Return list of sample files to test."""
        return [f for f in SAMPLE_FILES if f.name not in SKIP_SAMPLES]

    def test_samples_dir_exists(self):
        """doc/samples directory exists."""
        assert SAMPLES_DIR.exists()
        assert SAMPLES_DIR.is_dir()

    def test_have_sample_files(self):
        """There are sample files to test."""
        assert len(SAMPLE_FILES) > 0

    @pytest.mark.parametrize(
        "sample_file",
        [f for f in SAMPLE_FILES if f.name not in SKIP_SAMPLES],
        ids=lambda f: f.name
    )
    def test_sample_loads_as_module(self, sample_file):
        """Sample file can be loaded as a Python module."""
        # Just verify the file can be imported without errors
        module = get_module_from_path(sample_file)
        assert module is not None

    @pytest.mark.parametrize(
        "sample_file",
        [f for f in SAMPLE_FILES if f.name not in SKIP_SAMPLES],
        ids=lambda f: f.name
    )
    def test_sample_has_task_creators(self, sample_file):
        """Sample file contains task_* functions."""
        module = get_module_from_path(sample_file)
        creators = find_task_creators(module)

        # Most samples should have task creators
        # Some are supporting modules (we skip those)
        if sample_file.name.startswith('my_'):
            pytest.skip(f"{sample_file.name} is a supporting module")

        # Check for DOIT_CONFIG if no task creators
        has_config = hasattr(module, 'DOIT_CONFIG')
        if not creators and not has_config:
            # Some files may be support modules
            pytest.skip(f"{sample_file.name} has no task creators")

        # If it has creators, verify they're callable
        for name, creator in creators:
            assert callable(creator), f"{name} in {sample_file.name} is not callable"


class TestDocSamplesWithLoader:
    """Test sample files with ModuleTaskLoader."""

    @pytest.mark.parametrize(
        "sample_file",
        [f for f in SAMPLE_FILES if f.name not in SKIP_SAMPLES],
        ids=lambda f: f.name
    )
    def test_sample_with_module_loader(self, sample_file):
        """Sample file works with ModuleTaskLoader."""
        module = get_module_from_path(sample_file)
        creators = find_task_creators(module)

        if not creators:
            pytest.skip(f"{sample_file.name} has no task creators")

        # Use ModuleTaskLoader to load tasks
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        try:
            tasks = loader.load_tasks(cmd, [])
            # Verify we got some tasks
            assert isinstance(tasks, list)
            # Tasks may be empty for generators that need expansion
        except Exception as e:
            pytest.fail(f"Failed to load tasks from {sample_file.name}: {e}")


class TestSpecificSamples:
    """Test specific sample files in detail."""

    def test_hello_sample(self, tmp_path, monkeypatch):
        """hello.py sample produces expected output."""
        monkeypatch.chdir(tmp_path)

        module = get_module_from_path(SAMPLES_DIR / 'hello.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        assert len(tasks) == 1
        assert tasks[0].name == 'hello'
        assert 'hello.txt' in tasks[0].targets

    def test_parameters_sample(self):
        """parameters.py sample loads correctly."""
        module = get_module_from_path(SAMPLES_DIR / 'parameters.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # Should have multiple parameter tasks
        task_names = [t.name for t in tasks]
        assert 'py_params' in task_names
        assert 'cmd_params' in task_names

    def test_subtasks_sample(self):
        """subtasks.py sample generates subtasks."""
        module = get_module_from_path(SAMPLES_DIR / 'subtasks.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # Should have a group task and subtasks
        task_names = [t.name for t in tasks]
        assert 'create_file' in task_names

        # Check for subtasks
        subtask_count = sum(1 for t in tasks if t.subtask_of is not None)
        assert subtask_count >= 2, "Should have multiple subtasks"

    def test_getargs_sample(self):
        """getargs.py sample demonstrates value passing."""
        module = get_module_from_path(SAMPLES_DIR / 'getargs.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        task_names = [t.name for t in tasks]
        assert len(tasks) >= 2, "Should have producer and consumer tasks"

    def test_taskorder_sample(self):
        """taskorder.py demonstrates task dependencies."""
        module = get_module_from_path(SAMPLES_DIR / 'taskorder.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # Should have tasks with dependencies
        assert len(tasks) >= 2

    def test_group_sample(self):
        """group.py demonstrates task grouping via task_dep."""
        module = get_module_from_path(SAMPLES_DIR / 'group.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # group.py shows a group task (mygroup) that depends on foo and bar
        task_names = [t.name for t in tasks]
        assert 'foo' in task_names
        assert 'bar' in task_names
        assert 'mygroup' in task_names

        # mygroup should have no actions but depend on other tasks
        mygroup = next(t for t in tasks if t.name == 'mygroup')
        assert mygroup.task_dep == ['foo', 'bar']

    def test_clean_mix_sample(self):
        """clean_mix.py demonstrates clean actions."""
        module = get_module_from_path(SAMPLES_DIR / 'clean_mix.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # Should have tasks with clean definitions
        assert len(tasks) >= 1

    def test_uptodate_callable_sample(self):
        """uptodate_callable.py demonstrates uptodate checks."""
        module = get_module_from_path(SAMPLES_DIR / 'uptodate_callable.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # Should have task with uptodate callable
        assert len(tasks) >= 1
        # Check one task has uptodate
        task_with_uptodate = [t for t in tasks if t.uptodate]
        assert len(task_with_uptodate) >= 1

    def test_delayed_sample(self):
        """delayed.py demonstrates delayed task creation."""
        module = get_module_from_path(SAMPLES_DIR / 'delayed.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        # delayed creates tasks via DelayedLoader
        assert len(tasks) >= 1

    def test_custom_reporter_sample(self):
        """custom_reporter.py defines a valid reporter."""
        module = get_module_from_path(SAMPLES_DIR / 'custom_reporter.py')

        # Should define a reporter class
        assert hasattr(module, 'MyReporter') or any(
            name for name in dir(module) if 'reporter' in name.lower()
        )

    def test_checker_sample(self):
        """checker.py demonstrates custom file checkers."""
        module = get_module_from_path(SAMPLES_DIR / 'checker.py')
        loader = ModuleTaskLoader(module)
        loader.setup({})

        cmd = Command()
        tasks = loader.load_tasks(cmd, [])

        assert len(tasks) >= 1
