import os

from doit.util import md5sum

def test_md5():
    filePath = os.path.abspath(__file__+"/../sample_md5.txt")
    # result got using command line md5sum
    expected = "45d1503cb985898ab5bd8e58973007dd"
    assert expected == md5sum(filePath)
