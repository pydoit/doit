def task_version():
	return {'actions': ['bzr revno']}

def task_send_email():
	return {'actions': ['echo "TODO: send an email"'],
	        'result_dep': ['version']}
