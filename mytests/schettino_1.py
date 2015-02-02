def task_single():
    return {
        'file_dep': ["non_existing.txt"],
        'actions': ["cat non_existing.txt > output1.txt"],
        'targets': ["output1.txt"],
    }
