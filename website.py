"""dodo file create website html files"""

import os
import glob

from docutils.core import publish_parts
from mako import lookup, template


# generate API docs.
def task_epydoc():
    srcFiles = glob.glob("lib/doit/*.py")
    return {'action':"epydoc --config epydoc.config",
            'dependencies': srcFiles}


###### helper functions #####################

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
    parts = publish_parts(rst,writer_name='html')
    output.write("""<p class="title">%s</p>"""%parts['title'])
    output.write(parts['body'])
    output.close()
    return True


def mako2html(bodyFile,htmlFile):
    """create html from mako file. inherit from base.mako template."""
    mylookup = lookup.TemplateLookup(directories=['.'])
    mytemplate = template.Template("""
      <%%inherit file="doc/templates/base.mako"/> 
      <%%include file="%s"/> 
      """% bodyFile, 
      lookup=mylookup)

    output = open(htmlFile,"w")
    output.write(mytemplate.render())
    output.close()    
    return True


def create_folder(path):
    """Create folder given by "path" if it doesnt exist"""
    if not os.path.exists(path):
        os.mkdir(path)
    return True


########## build site ####################

rstPath = "doc/"
tempPath = "doc/temp/" 
htmlPath = "doc/html/"
templatePath = "doc/templates/"
docFiles = [f[4:-4] for f in glob.glob('doc/*.txt')]
makoFiles = ['examples']

baseTemplate = templatePath + "base.mako"

def task_create_temp_folder():
    buildFolder = tempPath
    return {'action':create_folder,
            'args': (buildFolder,)
            }


def task_rst():
    for rst in docFiles:                
        source = rstPath + rst + ".txt"
        target = tempPath + rst + ".html"
        yield {'action':rst2body,
               'name':source,
               'args':[source, target],
               'dependencies':[":create_temp_folder",source],
               'targets':[target]}


def task_html():
    # from ReST
    sources = [tempPath + body + ".html" for body in docFiles]
    targets = [htmlPath + body + ".html" for body in docFiles]
    # from mako templates
    sources += [templatePath + template + ".mako" for template in makoFiles]
    targets += [htmlPath + template + ".html" for template in makoFiles]

    for source,target in zip(sources,targets):
        yield {'action':mako2html,
               'name':source,
               'args':[source, target],
               'dependencies':[source],
               'targets':[target]}


