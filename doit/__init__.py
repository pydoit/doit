"""doit - Automation Tool

The MIT License

Copyright (c) 2008-2011 Eduardo Naufel Schettino

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

__version__ = (0, 15, 0)

# Use simplejson or Python 2.6 json
# simplejson is much faster that py26:json. so use simplejson if available
try:
    import simplejson
    json = simplejson
except ImportError: # pragma: no cover
    import json
json # pyflakes



# used to save variable values passed from command line
CMDLINE_VARS = None

def reset_vars():
    global CMDLINE_VARS
    CMDLINE_VARS = {}

def get_var(name, default=None):
    return CMDLINE_VARS.get(name, default)

def set_var(name, value):
    CMDLINE_VARS[name] = value
