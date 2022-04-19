import pathlib

import click
from rich.console import Console
from doit import create_after, task_params
from doit.api import run_tasks
from doit.cmd_base import ModuleTaskLoader

from pydevtool import custom_theme, DoitRichReporter, Linter
from pydevtool import Context, CliGroup, run_doit_task, Task


CONSOLE = Console(theme=custom_theme)
REPORTER = DoitRichReporter(CONSOLE)
DOIT_CONFIG = {
    'default_tasks': [],
    'verbosity': 2,
    'continue': True,
}


@create_after()
def task_pyflakes():
    print('creating tasks')
    linter = Linter(CONSOLE, config_file='setup.cfg')
    count = 0
    for fn in pathlib.Path("doit").glob('*.py'):
        count += 1
        yield {
            'name': fn,
            'actions': [(linter, [fn])],
            'file_dep': [fn],
        }
    REPORTER.add_progress_bar('pyflakes', count)



##########################################################

def run_doit_task(tasks):
    """
      :param tasks: (dict) task_name -> {options}
    """
    loader = ModuleTaskLoader(globals())
    config = DOIT_CONFIG.copy()
    config['reporter'] = REPORTER
    return run_tasks(loader, tasks, extra_config={'GLOBAL': config})


CONTEXT = Context({
    'no_build': click.Option(
        ["--no-build", "-n"], default=False, is_flag=True,
        help=(":wrench: do not build the project"
              " (note event python only modification require build)")),
})


@click.group(cls=CliGroup)
@click.pass_context
def cli(ctx, **kwargs):
    """Developer Tool
    """
    ctx.ensure_object(dict)
    for opt_name in CONTEXT.options.keys():
        ctx.obj[opt_name] = kwargs.get(opt_name)
cli.params.extend(CONTEXT.options.values())
cli.run_doit_task = run_doit_task


@task_params([{'name': 'output_file', 'long': 'output-file', 'default': None,
               'help': 'Redirect report to a file'}])
def task_flake8(output_file):
    """Run flake8 over the code base and benchmarks."""
    opts = ''
    if output_file:
        opts += f'--output-file={output_file}'
    return {
        'actions': [f"flake8 {opts} doit"],
        'doc': 'Lint scipy and benchmarks directory',
    }



@cli.cls_cmd('lint')
class Lint():
    """:dash: run flake8, and check PEP 8 compliance on branch diff."""
    output_file = click.Option(
        ['--output-file'], default=None, help='Redirect report to a file')

    def run(output_file):
        opts = {'output_file': output_file}
        # run_doit_task({'flake8': opts})
        run_doit_task({'pyflakes': opts})


@cli.cls_cmd('test')
class Test(Task):
    """Run tests"""

    @classmethod
    def run(cls):
        print('Running tests...')




if __name__ == '__main__':
    cli()
