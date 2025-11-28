#!/usr/bin/env python3
"""
Setup script for the programmatic doit demo.

This creates a simple file-based build system:
- src/module_a.py, src/module_b.py, src/module_c.py (source files)
- Each source file gets "compiled" to build/module_X.out
- A final link step combines all .out files into build/app

Run this first to set up the demo files, then use run_demo.py to execute tasks.
"""

import os
import shutil
from pathlib import Path

DEMO_DIR = Path(__file__).parent / "workspace"


def setup():
    """Create the demo workspace with source files."""
    # Clean up any existing workspace
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)

    # Create directories
    src_dir = DEMO_DIR / "src"
    build_dir = DEMO_DIR / "build"
    src_dir.mkdir(parents=True)
    build_dir.mkdir(parents=True)

    # Create source files
    sources = {
        "module_a.py": '''
def greet():
    return "Hello from module A!"
''',
        "module_b.py": '''
def calculate(x, y):
    return x + y
''',
        "module_c.py": '''
def format_output(msg):
    return f"[OUTPUT] {msg}"
''',
    }

    for name, content in sources.items():
        (src_dir / name).write_text(content.strip() + "\n")
        print(f"Created: src/{name}")

    # Create the doit database directory
    db_dir = DEMO_DIR / ".doit_db"
    db_dir.mkdir(exist_ok=True)

    print(f"\nWorkspace created at: {DEMO_DIR}")
    print("\nNext steps:")
    print("  1. Run: python run_demo.py        # Execute all tasks")
    print("  2. Run: python run_demo.py        # Run again (all up-to-date)")
    print("  3. Run: python touch_file.py a    # Modify module_a")
    print("  4. Run: python run_demo.py        # Only module_a recompiles")


if __name__ == "__main__":
    setup()
