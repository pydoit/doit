#!/usr/bin/env python3
"""
Demo of dynamic task injection with the programmatic interface.

This shows how to add tasks during iteration based on results
of previous tasks - useful for:
- Discovering files to process
- Building dependency graphs dynamically
- Conditional task execution

No setup required - this demo uses in-memory execution.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doit import DoitEngine, InMemoryStateStore


def discover_items():
    """Simulate discovering items that need processing."""
    print("    Discovering items...")
    # In real code, this might scan a directory, query an API, etc.
    return {"items": ["apple", "banana", "cherry"]}


def process_item(item):
    """Process a single discovered item."""
    print(f"    Processing: {item}")
    return True


def summarize(items):
    """Create a summary of all processed items."""
    print(f"    Creating summary for: {items}")
    return True


def run_dynamic_demo():
    """Demo of adding tasks dynamically during iteration."""
    print("=" * 60)
    print("Demo: Dynamic Task Injection")
    print("=" * 60)
    print()
    print("This demo shows how to add tasks during iteration.")
    print("We start with just a 'discover' task, then add processing")
    print("tasks based on what we discover.")
    print()

    # Start with just a discover task
    initial_tasks = [{
        "name": "discover",
        "actions": [discover_items],
        "doc": "Discover items to process",
    }]

    discovered_items = []

    with DoitEngine(initial_tasks, store=InMemoryStateStore()) as engine:
        for wrapper in engine:
            print(f"Task: {wrapper.name}")

            if wrapper.should_run:
                wrapper.execute_and_submit()

                # After discover runs, add processing tasks for each item
                if wrapper.name == "discover":
                    items = wrapper.values.get("items", [])
                    discovered_items = items
                    print(f"    Discovered {len(items)} items, adding tasks...")

                    # Add a task for each discovered item
                    for item in items:
                        engine.add_task({
                            "name": f"process_{item}",
                            "actions": [(process_item, [item])],
                            "task_dep": ["discover"],
                            "doc": f"Process {item}",
                        })

                    # Add a summary task that depends on all processing
                    engine.add_task({
                        "name": "summarize",
                        "actions": [(summarize, [items])],
                        "task_dep": [f"process_{item}" for item in items],
                        "doc": "Summarize all processing",
                    })

    print()
    print("=" * 60)
    print("All tasks completed!")
    print(f"Discovered and processed: {discovered_items}")
    print("=" * 60)


if __name__ == "__main__":
    run_dynamic_demo()
