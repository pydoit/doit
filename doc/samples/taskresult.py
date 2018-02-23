from doit.tools import result_dep

def task_version():
	return {'actions': ["hg tip --template '{rev}:{node}'"]}

def task_send_email():
	return {'actions': ['echo "TODO: send an email"'],
	        'uptodate': [result_dep('version')]}
