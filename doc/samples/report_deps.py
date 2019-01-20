DOIT_CONFIG = {'action_string_formatting': 'both'}

def task_report_deps():
    """
    Report dependencies and changed dependencies to a file.
    """
    return {
        'file_dep': ['req.in', 'req-dev.in'],
        'actions': [
                # New style formatting
                'echo D: {dependencies}, CH: {changed} > {targets}',
                # Old style formatting
                'cat %(targets)s',
                ],
        'targets': ['report.txt'],
        }

