from doit.cmd_base import Command


class Init(Command):
    doc_purpose = 'create a project scaffolding'
    doc_usage = ''
    doc_description = """This is a multiline command description.
It will be displayed on `doit help init`"""

    def execute(self, opt_values, pos_args):
        print("TODO: create some files for my project")
