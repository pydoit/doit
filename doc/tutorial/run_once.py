
def run_once(task, values):
    def save_executed():
        return {'run-once': True}
    task.insert_action(save_executed)
    return values.get('run-once', False)
