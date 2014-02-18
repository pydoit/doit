import sys
import subprocess

import pytest

sys # keep pyflakes quiet
@pytest.mark.skipif('sys.version_info < (2,7,0)')
def test_execute():
    assert 0 == subprocess.call(['python', '-m', 'doit', 'list'])

