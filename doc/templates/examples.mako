## something like the tags "include" and "text" together
<%def name="include_text(filePath)">
   <% 
       import os
       f = open(filePath)
       content = f.read()
       f.close()
   %>
   <pre class="literal-block">
   ${content | h}
   </pre>
</%def>


<p class="title">Examples</p>
<p>These are examples extracted from the DoIt project itself.</p> 

<h2> DoIt website </h2>
<p>This script is used to build this website. The content is mostly written in ReST. The build script first converts the ReST to html. The generated html is inserted into the base layout given by mako templates.</p>

${include_text("website.py")}

<h2> DoIt pre-commit </h2>
<p>This script is used to pychecker and nosetests on DoIt source code.</p>

${include_text("dodo.py")}

