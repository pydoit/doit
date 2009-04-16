url = "http://svn.dojotoolkit.org/src/util/trunk/shrinksafe/shrinksafe.jar"
shrinksafe = "shrinksafe.jar"

jsFile = "file1.js"
compFile = "compressed1.js"

def task_shrink():
    return {'action': 'java -jar %s %s > %s'% (shrinksafe, jsFile, compFile),
            'dependencies': [shrinksafe]
            }

def task_get_shrinksafe():
    return {'action': "wget %s"% url,
            'targets': [shrinksafe],
            'dependencies': [True]
            }
