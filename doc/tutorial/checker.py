from pathlib import Path

def task_checker():
    return {'actions': ["pyflakes sample.py"],
            'file_dep': ["sample.py"]}

def task_checker_pathlib():
    sample_path = Path("sample.py")
    return {'actions': [["pyflakes", sample_path]],
            'file_dep': [sample_path]}
