import doit

DOIT_CONFIG = dict(
    verbosity=2,
)


def task_create():
    # dependency manager is defined for all code inside the generator:
    dep_manager = doit.Globals.dep_manager

    def action():
        # assume some involved logic to define ident:
        ident = 42
        print('Created', ident)

        # store for clean:
        return dict(created=ident)

    def clean(task):
        result = dep_manager.get_result(task.name)
        if result:
            ident = result['created']
            print('Deleted', ident)

            # possibly forget the task, after it was cleaned:
            dep_manager.remove(task.name)

    return dict(
        actions=[action],
        clean=[clean],
    )
