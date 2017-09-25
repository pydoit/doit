def task_report_deps():
    """report dependencies and changed dependencies to a file
    """
    return {
        'file_dep': ['req.in', 'req-dev.in'],
        'actions': ['echo D: %(dependencies)s, CH: %(changed)s > %(targets)s'],
        'targets': ['report.txt'],
        }
