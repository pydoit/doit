def task_version():
	return {'actions': ['bzr version-info --custom --template="{revno}\n"']}

def task_send_email():
	return {'actions': ['echo "TODO: send an email"'],
	        'dependencies': ['?version']}
