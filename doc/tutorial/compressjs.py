""" dodo file - compress javascript files and pack them together"""

url = "http://svn.dojotoolkit.org/src/util/trunk/shrinksafe/shrinksafe.jar"
shrinksafe = "shrinksafe.jar"
jsPath = "./"
buildPath = "build/"
jsFiles = ["file1.js", "file2.js"]

sourceFiles = [jsPath + f for f in jsFiles]
compressedFiles = [jsPath + buildPath + f + ".compressed" for f in jsFiles]


def task_get_shrinksafe():
    return {'action': "wget %s"% url,
            'targets': [shrinksafe],
            'dependencies': [True]
            }

def task_shrink_js():
    for jsFile,compFile in zip(sourceFiles,compressedFiles):
        action = 'java -jar %s %s > %s'% (shrinksafe, jsFile, compFile),
        yield {'action':action,
               'name':jsFile,
               'dependencies':(shrinksafe, buildPath, jsFile),
               'targets':(compFile,)
               }

def task_pack_js():
    output = jsPath + 'compressed.js'
    input = compressedFiles
    action = "cat %s > %s"% (" ".join(input), output)
    return {'action': action,
            'dependencies': input,
            'targets':[output]}

