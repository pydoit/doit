""" dodo file - compress javascript files """

import os

jsPath = "./"
jsFiles = ["file1.js", "file2.js"]

sourceFiles = [jsPath + f for f in jsFiles]
compressedFiles = [jsPath + "build/" + f + ".compressed" for f in jsFiles]

def create_folder(path):
    """Create folder given by "path" if it doesnt exist"""
    if not os.path.exists(path):
        os.mkdir(path)
    return True

def task_create_build_folder():
    buildFolder = jsPath + "build"
    return {'action':create_folder,
            'args': (buildFolder,)
            }

def task_shrink_js():
    for jsFile,compFile in zip(sourceFiles,compressedFiles):
        action = 'java -jar custom_rhino.jar -c %s > %s'% (jsFile, compFile)
        yield {'action':action,
               'name':jsFile,
               'dependencies':(":create_build_folder", jsFile,),
               'targets':(compFile,)
               }

def task_pack_js():
    output = jsPath + 'compressed.js'
    input = compressedFiles
    action = "cat %s > %s"% (" ".join(input), output)
    return {'action': action,
            'dependencies': input,
            'targets':[output]}

