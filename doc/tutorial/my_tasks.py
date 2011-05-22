
def task(*fn, **kwargs):
    # decorator without parameters
    if fn:
        function = fn[0]
        function.task_metadata = {}
        return function

    # decorator with parameters
    def wrap(function):
        function.task_metadata = kwargs
        return function
    return wrap



@task
def simple():
    print "thats all folks"

@task(output=['out1.txt', 'out2.txt'])
def create(to_be_created):
    print "I should create these files: %s" % " ".join(to_be_created)

@task(input=['my_input.txt'], output=['my_output_result.txt'])
def process(in_, out_):
    print "processing %s" % in_[0]
    print "creating %s" % out_[0]



