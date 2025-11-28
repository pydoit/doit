#!/usr/bin/env python3
"""
Utility to "modify" a source file to trigger rebuilds.

Usage:
    python touch_file.py a        # Modify module_a.py
    python touch_file.py b        # Modify module_b.py
    python touch_file.py c        # Modify module_c.py
    python touch_file.py all      # Modify all source files

This appends a comment with timestamp to the file, changing its content
and triggering doit to re-run dependent tasks.
"""

import sys
import time
from pathlib import Path

DEMO_DIR = Path(__file__).parent / "workspace"
SRC_DIR = DEMO_DIR / "src"


def touch_module(module_name):
    """Add a timestamp comment to a module file."""
    src_file = SRC_DIR / f"module_{module_name}.py"

    if not src_file.exists():
        print(f"Error: {src_file} not found. Run setup_demo.py first.")
        return False

    content = src_file.read_text()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # Remove any existing "Modified:" comment and add new one
    lines = content.split("\n")
    lines = [l for l in lines if not l.startswith("# Modified:")]
    lines.append(f"# Modified: {timestamp}")

    src_file.write_text("\n".join(lines))
    print(f"Modified: src/module_{module_name}.py")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    arg = sys.argv[1].lower()

    if arg == "all":
        for m in ["a", "b", "c"]:
            touch_module(m)
    elif arg in ["a", "b", "c"]:
        touch_module(arg)
    else:
        print(f"Unknown module: {arg}")
        print("Use: a, b, c, or all")
        return 1

    print("\nNow run: python run_demo.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
