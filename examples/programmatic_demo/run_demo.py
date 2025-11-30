#!/usr/bin/env python3
"""
Demo of the programmatic doit interface.

This script shows:
1. Defining tasks as Python dicts
2. Using DoitEngine to iterate through tasks
3. File dependency tracking (only re-runs when sources change)
4. Task dependencies (link waits for all compiles)

Run setup_demo.py first to create the workspace.
"""

import sys
import time
from pathlib import Path

# Add doit to path if running from examples directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doit import DoitEngine, TaskStatus

DEMO_DIR = Path(__file__).parent / "workspace"
SRC_DIR = DEMO_DIR / "src"
BUILD_DIR = DEMO_DIR / "build"
DB_FILE = str(DEMO_DIR / ".doit_db" / "demo.db")


def compile_module(src_path, out_path):
    """Simulate compiling a module (just copies with a header)."""
    content = Path(src_path).read_text()
    output = f"# Compiled from {src_path} at {time.strftime('%H:%M:%S')}\n{content}"
    Path(out_path).write_text(output)
    return True


def link_modules(out_files, app_path):
    """Simulate linking modules together."""
    combined = f"# Linked application at {time.strftime('%H:%M:%S')}\n"
    combined += "# " + "=" * 50 + "\n\n"
    for out_file in sorted(out_files):
        combined += f"# From: {out_file}\n"
        combined += Path(out_file).read_text() + "\n"
    Path(app_path).write_text(combined)
    return True


def create_tasks():
    """Create task definitions for the build system."""
    tasks = []
    modules = ["module_a", "module_b", "module_c"]

    # Compile tasks - one per module
    for module in modules:
        src_path = str(SRC_DIR / f"{module}.py")
        out_path = str(BUILD_DIR / f"{module}.out")

        tasks.append({
            "name": f"compile_{module}",
            "actions": [(compile_module, [src_path, out_path])],
            "file_dep": [src_path],
            "targets": [out_path],
            "doc": f"Compile {module}.py to {module}.out",
        })

    # Link task - depends on all compile tasks
    out_files = [str(BUILD_DIR / f"{m}.out") for m in modules]
    app_path = str(BUILD_DIR / "app")

    tasks.append({
        "name": "link",
        "actions": [(link_modules, [out_files, app_path])],
        "file_dep": out_files,
        "targets": [app_path],
        "task_dep": [f"compile_{m}" for m in modules],
        "doc": "Link all modules into final app",
    })

    return tasks


def run_build():
    """Run the build using the programmatic interface."""
    if not DEMO_DIR.exists():
        print("Error: Workspace not found. Run setup_demo.py first.")
        return 1

    tasks = create_tasks()

    print("=" * 60)
    print("Running build with doit programmatic interface")
    print("=" * 60)
    print()

    executed = []
    skipped = []

    with DoitEngine(tasks, db_path=DB_FILE) as engine:
        for wrapper in engine:
            task_name = wrapper.name
            status = wrapper.status

            if wrapper.should_run:
                print(f"[RUN]      {task_name}")
                result = wrapper.execute_and_submit()
                if result is None:
                    executed.append(task_name)
                    print(f"           -> Success")
                else:
                    print(f"           -> FAILED: {result}")
                    return 1
            else:
                reason = wrapper.skip_reason or "up-to-date"
                print(f"[SKIP]     {task_name} ({reason})")
                skipped.append(task_name)

    print()
    print("=" * 60)
    print(f"Executed: {len(executed)} tasks")
    print(f"Skipped:  {len(skipped)} tasks (up-to-date)")
    print("=" * 60)

    if executed:
        print("\nTasks that ran:")
        for t in executed:
            print(f"  - {t}")

    return 0


if __name__ == "__main__":
    sys.exit(run_build())
