import subprocess
import unittest
from sys import executable

from tests.support import DepfileNameMixin


class TestMain(DepfileNameMixin, unittest.TestCase):
    def test_execute(self):
        self.assertEqual(0, subprocess.call(
            [executable, '-m', 'doit', 'list', '--db-file', self.depfile_name]))
