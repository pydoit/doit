
def fake_get_value_from_db():
    return 5

def check_outdated(task, values):
    total = fake_get_value_from_db()
    return total > 10


def task_put_more_stuff_in_db():
    def put_stuff(): pass
    return {'actions': [put_stuff],
            'uptodate': [check_outdated],
            }
