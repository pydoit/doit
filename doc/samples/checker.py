def task_checker():
    return {'actions': ["pyflakes sample.py"],
            'file_dep': ["sample.py"]}
