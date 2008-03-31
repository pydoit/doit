"""Automate release process. 

This is "dodo" file (suposed to be run with DoIt).
"""

def task_revision():
    return "bzr version-info > revision.txt"

def task_sdist():
    return "python setup.py sdist"

def task_epydoc():
    return "epydoc --config epydoc.config"


###########################

from docutils.core import publish_parts
def rst2body(rstFile,bodyFile):
    """convert reStructured file to html and extract only the body of the html.

    @param rstFile: input rst file path
    @param bodyFile: output htmlt body file path
    """
    input = open(rstFile)
    try:
        rst = input.read()
    finally:
        input.close()
        
    output = open(bodyFile,"w")
    output.write(publish_parts(rst,writer_name='html')['body'])
    output.close()
    return True


def task_rst2html():
    rstPath = "doc/"
    htmlPath = "doc/html/"
    rstFiles = ["developer.txt","reference.txt"]

    for rst in rstFiles:
        source = rstPath+rst
        target = htmlPath+rst[:-4]+".html"
        yield {'action':rst2body,
               'name':source,
               'args':[source, target],
               'dependencies':[source],
               'targets':[target]}
