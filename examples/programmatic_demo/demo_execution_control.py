#!/usr/bin/env python3
"""
Demo of fine-grained execution control with the programmatic interface.

This shows the different ways to control task execution:
- execute_and_submit(): Run and save results (convenience)
- execute() + submit(): Run, inspect, then save
- Skip execution entirely based on custom logic

No setup required - uses in-memory execution.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doit import DoitEngine, TaskStatus, InMemoryStateStore


def task_a():
    print("    Running task A")
    return {"status": "ok", "value": 42}


def task_b():
    print("    Running task B")
    return True


def task_c_might_fail(should_fail=False):
    print("    Running task C")
    if should_fail:
        return False  # This signals failure
    return True


def task_d():
    print("    Running task D")
    return True


def run_control_demo():
    """Demo different execution control patterns."""
    print("=" * 60)
    print("Demo: Execution Control Patterns")
    print("=" * 60)
    print()

    tasks = [
        {"name": "task_a", "actions": [task_a], "doc": "Returns a dict with values"},
        {"name": "task_b", "actions": [task_b], "doc": "Simple success"},
        {"name": "task_c", "actions": [(task_c_might_fail, [], {"should_fail": False})],
         "doc": "Might fail"},
        {"name": "task_d", "actions": [task_d], "task_dep": ["task_a"],
         "doc": "Depends on task_a"},
    ]

    print("Pattern 1: execute_and_submit() - Simple all-in-one")
    print("-" * 40)

    with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
        for wrapper in engine:
            if not wrapper.should_run:
                print(f"  {wrapper.name}: skipped ({wrapper.skip_reason})")
                continue

            result = wrapper.execute_and_submit()
            if result is None:
                print(f"  {wrapper.name}: success")
                if wrapper.values:
                    print(f"    -> values: {wrapper.values}")
            else:
                print(f"  {wrapper.name}: FAILED - {result}")

    print()
    print("Pattern 2: execute() then submit() - Inspect before saving")
    print("-" * 40)

    with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
        for wrapper in engine:
            if not wrapper.should_run:
                print(f"  {wrapper.name}: skipped")
                continue

            # Execute but don't submit yet
            result = wrapper.execute()
            print(f"  {wrapper.name}: executed, result={result}")

            # Inspect the result before deciding to submit
            if result is None:
                print(f"    -> Execution successful, submitting...")
                wrapper.submit()
            else:
                print(f"    -> Execution failed, submitting failure...")
                wrapper.submit()  # Still submit to record the failure

    print()
    print("Pattern 3: Custom skip logic")
    print("-" * 40)

    # Skip tasks based on custom criteria
    tasks_to_skip = {"task_b"}  # Pretend we want to skip task_b

    with DoitEngine(tasks, store=InMemoryStateStore()) as engine:
        for wrapper in engine:
            if wrapper.name in tasks_to_skip:
                print(f"  {wrapper.name}: CUSTOM SKIP (user choice)")
                continue  # Don't execute or submit - just skip

            if not wrapper.should_run:
                print(f"  {wrapper.name}: skipped ({wrapper.skip_reason})")
                continue

            wrapper.execute_and_submit()
            print(f"  {wrapper.name}: executed")

    print()
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_control_demo()
