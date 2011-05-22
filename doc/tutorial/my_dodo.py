
DOIT_CONFIG = {'verbosity': 2}

TASKS_MODULE = __import__('my_tasks')

def task_do():
    # get functions that are tasks from module
    for name in dir(TASKS_MODULE):
        item = getattr(TASKS_MODULE, name)
        if not hasattr(item, 'task_metadata'):
            continue

        # get task metadata attached to the function
        metadata = item.task_metadata

        # get name of task from function name
        metadata['name'] = item.__name__

        # *I* dont like the names file_dep, targets. So I use 'input', 'output'
        class Sentinel: pass
        input_ = metadata.pop('input', Sentinel)
        output_ = metadata.pop('output', Sentinel)
        args = []
        if input_ != Sentinel:
            metadata['file_dep'] = input_
            args.append(input_)
        if output_ != Sentinel:
            metadata['targets'] = output_
            args.append(output_)

        # the action is the function iteself
        metadata['actions'] = [(item, args)]

        yield metadata

