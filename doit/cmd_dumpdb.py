import anydbm

from .cmd_base import Command, opt_depfile

class DumpDB(Command):
    """dump dependency DB"""
    doc_purpose = 'dump dependency DB'
    doc_usage = ''
    doc_description = None

    cmd_options = (opt_depfile,)

    def execute(self, opt_values, pos_args):
        dep_file = opt_values['dep_file']
        data = anydbm.open(dep_file)
        for key, value in data.iteritems():
            print "{key} -> {value}".format(key=key, value=value)
