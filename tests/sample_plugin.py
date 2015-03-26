from doit.cmd_base import Command

class MyCmd(Command):
    name = 'mycmd'
    doc_purpose = 'test extending doit commands'
    doc_usage = '[XXX]'
    doc_description = 'my command description'

    def execute(self, opt_values, pos_args): # pragma: no cover
        print("this command does nothing!")
