# Programmatic Doit Interface - Demo Scripts

This directory contains demo scripts showing how to use doit's new programmatic interface.

## Quick Start

```bash
cd examples/programmatic_demo

# 1. Set up a simple build system demo
python setup_demo.py

# 2. Run the build (all tasks execute)
python run_demo.py

# 3. Run again (all tasks skipped - up-to-date)
python run_demo.py

# 4. Modify a source file
python touch_file.py a

# 5. Run again (only affected tasks re-run)
python run_demo.py
```

## Demo Scripts

### `setup_demo.py`
Creates a workspace with source files that simulate a build system:
- `workspace/src/module_a.py`
- `workspace/src/module_b.py`
- `workspace/src/module_c.py`

### `run_demo.py`
Runs a build using the programmatic interface. Shows:
- Task definition as Python dicts
- File dependency tracking
- Up-to-date detection
- Task dependencies

### `touch_file.py`
Modifies source files to trigger rebuilds:
```bash
python touch_file.py a      # Modify module_a only
python touch_file.py all    # Modify all modules
```

### `demo_dynamic_tasks.py`
Shows dynamic task injection - adding tasks during iteration:
```bash
python demo_dynamic_tasks.py
```
No setup required - uses in-memory execution.

### `demo_execution_control.py`
Shows different execution control patterns:
```bash
python demo_execution_control.py
```
- `execute_and_submit()` - convenience method
- `execute()` + `submit()` - inspect before saving
- Custom skip logic

## Key Concepts

### Basic Usage
```python
from doit import DoitEngine

tasks = [
    {'name': 'build', 'actions': [my_function], 'file_dep': ['input.txt']},
]

with DoitEngine(tasks) as engine:
    for wrapper in engine:
        if wrapper.should_run:
            wrapper.execute_and_submit()
```

### In-Memory Execution
Use `InMemoryStateStore` for no database persistence:
```python
from doit import DoitEngine, InMemoryStateStore

with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
    ...
```

### Dynamic Task Injection
Add tasks based on results of previous tasks:
```python
from doit import DoitEngine, InMemoryStateStore

with DoitEngine(initial_tasks, store=InMemoryStateStore()) as engine:
    for wrapper in engine:
        if wrapper.should_run:
            wrapper.execute_and_submit()

        if wrapper.name == 'discover':
            for item in wrapper.values['items']:
                engine.add_task({
                    'name': f'process_{item}',
                    'actions': [...],
                })
```

### TaskWrapper Properties
- `wrapper.name` - task name
- `wrapper.should_run` - True if task needs execution
- `wrapper.skip_reason` - why task was skipped (if applicable)
- `wrapper.status` - current TaskStatus
- `wrapper.values` - task output values (after execution)
- `wrapper.task` - underlying Task object

### TaskWrapper Methods
- `execute()` - run the task, return error or None
- `submit()` - save results to dependency tracking
- `execute_and_submit()` - convenience combo
