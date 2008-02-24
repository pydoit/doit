import doctest

def test_tutorial():
    (failure_count, test_count) = doctest.testfile("tutorial.txt")
    assert 0 == failure_count
