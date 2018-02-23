from pathlib import Path

def task_compile():
    working_directory = Path('.')
    # Path.glob returns an iterator so turn it into a list
    headers = list(working_directory.glob('*.h'))
    for source_file in working_directory.glob('*.c'):
        object_file = source_file.with_suffix('.o')
        yield {
            'name': object_file.name,
            'actions': [['cc', '-c', source_file]],
            'file_dep': [source_file] + headers,
            'targets': [object_file],
        }
