from doit.tools import result_dep

def task_version():
	return {'actions': ['bzr revno']}

def task_send_email():
	return {'actions': ['echo "TODO: send an email"'],
	        'uptodate': result_dep('version')}
