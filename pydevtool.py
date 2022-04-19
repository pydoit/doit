import re


##########################################
# doit / click integration through custom class interface

import click
from click.globals import get_current_context
from rich_click import RichCommand, RichGroup
from doit.task import Task as DoitTask
from doit.cmd_base import ModuleTaskLoader
from doit.api import run_tasks



class Context():
    """Higher level to allow some level of Click.context with doit"""
    def __init__(self, options: dict):
        self.options = options
        self.vals = {}

    def get(self, save=None):
        # try to get from Click
        ctx = get_current_context(silent=True)
        if ctx:
            return ctx.obj
        else:
            if save:
                for name in self.options.keys():
                    if name in save:
                        self.vals[name] = save[name]
            return self.vals


param_type_map = {
    'text': str,
    'boolean': bool,
    'integer': int,
}


def param_click2doit(name: str, val: click.Parameter):
    """Convert click param to dict used by doit.cmdparse"""
    pd = {
        'name': name,
        'type': param_type_map[val.type.name],  # FIXME: add all types
        'default': val.default,
        'help': getattr(val, 'help', ''),
        'metavar': val.metavar,
    }
    for opt in val.opts:
        if opt[:2] == '--':
            pd['long'] = opt[2:]
        elif opt[0] == '-':
            pd['short'] = opt[1:]
    return pd


# convert click.types.ParamType.name to doit param type
CAMEL_PATTERN = re.compile(r'(?!^)([A-Z]+)')


def to_camel(name):
    return CAMEL_PATTERN.sub(r'-\1', name).lower()


def run_as_py_action(cls):
    """used by doit loader to create task instances"""
    if cls is Task:
        return
    task_kwargs = getattr(cls, 'TASK_META', {})
    return DoitTask(
        # convert name to kebab-case
        name=to_camel(cls.__name__),
        doc=cls.__doc__,
        actions=[cls.run],
        params=cls._params,
        **task_kwargs,
    )


class MetaclassDoitTask(type):
    def __new__(meta_cls, name, bases, dct):
        # params/opts from Context and Option attributes
        cls = super().__new__(meta_cls, name, bases, dct)
        params = []
        if ctx := getattr(cls, 'ctx', None):
            for ctx_opt in ctx.options.values():
                params.append(param_click2doit(ctx_opt.name, ctx_opt))
        for attr_name, val in cls.__dict__.items():
            if isinstance(val, click.Parameter):
                params.append(param_click2doit(attr_name, val))
        cls._params = params

        task_basename = to_camel(cls.__name__)
        if hasattr(cls, 'task_meta'):
            def creator(**kwargs):
                task_meta = cls.task_meta(**kwargs)
                if 'basename' not in task_meta:
                    task_meta['basename'] = task_basename
                if 'doc' not in task_meta:
                    task_meta['doc'] = cls.__doc__
                return task_meta
            creator._task_creator_params = cls._params
        else:
            def creator():
                return run_as_py_action(cls)
        creator.basename = task_basename
        cls.create_doit_tasks = creator
        return cls


class Task(metaclass=MetaclassDoitTask):
    """Base class to define doit task and/or click command"""

    @classmethod
    def opt_defaults(cls):
        """helper used by another click commands to call this command"""
        return {p['name']: p['default'] for p in cls._params}


class CliGroup(RichGroup):
    COMMAND_CLASS = RichCommand
    run_doit_task = None

    def cls_cmd(self, name):
        """class decorator, convert to click.Command"""
        def register_click(cls):
            # get options/arguments for class definition
            params = []
            for attr_name, attr_val in cls.__dict__.items():
                if isinstance(attr_val, click.Parameter):
                    params.append(attr_val)

            if issubclass(cls, Task):
                # run as doit task
                def callback(**kwargs):
                    self.run_doit_task({name: kwargs})
            else:
                # run as plain function
                def callback(**kwargs):
                    cls.run(**kwargs)

            click_cmd = RichCommand(
                name=name,
                callback=callback,
                help=cls.__doc__,
                params=params,
            )
            self.add_command(click_cmd)
            return cls
        return register_click


def run_doit_task(tasks):
    """
      :param tasks: (dict) task_name -> {options}
    """
    loader = ModuleTaskLoader(globals())
    doit_config = {
        'verbosity': 2,
        'reporter': 'zero',
    }
    return run_tasks(loader, tasks, extra_config={'GLOBAL': doit_config})




###########################################################

from rich.console import Console
from rich.progress import Progress, BarColumn, TimeElapsedColumn
from rich.theme import Theme
from rich.panel import Panel
from doit.exceptions import TaskFailed as DoitTaskFailed

from pyflakes.api import checkPath
from pyflakes.reporter import Reporter as FlakeReporter
import pycodestyle



custom_theme = Theme({
    "name": "dim cyan",
    "event": "yellow",
    "failure": "red",
    "success": "green",
    "up-to-date": "cyan",
})


class DoitDebugReporter():
    desc = 'debug reporter - print out reporter events'

    def __init__(self, outstream, options):
        self.console = Console(theme=custom_theme)

    def initialize(self, tasks, selected_tasks):
        """called just after tasks have been loaded before execution starts"""
        self.console.print('[event]INITIALIZE [name]')
        # console.print(Panel(str(tasks), title="tasks"))
        # console.print(Panel(str(selected_tasks), title="selected"))

    def get_status(self, task):
        self.console.print(f'[event]STATUS [name]{task.name}')

    def execute_task(self, task):
        self.console.print(f'[event]EXECUTE [name]{task.name}')

    def skip_uptodate(self, task):
        self.console.print(f'[up-to-date]UP-TO-DATE [name]{task.name}')

    def skip_ignore(self, task):
        self.console.print(f'[event]SKIP [name]{task.name}')

    def add_failure(self, task, exception):
        self.console.print(f'[failure]FAILURE [name]{task.name}')
        if not isinstance(exception, DoitTaskFailed):
            self.console.print(Panel(str(exception), title="Error"))

    def add_success(self, task):
        self.console.print(f'[success]SUCCESS [name]{task.name}')

    def complete_run(self):
        self.console.print('[event]COMPLETE [name]')

    def cleanup_error(self, exception):
        self.console.print('[event]CLEANUP ERROR [name]')

    def runtime_error(self, msg):
        self.console.print('[event]ERROR [name]')
        self.console.print(Panel(msg, title="Error"))

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        self.console.print('[event]TEARDOWN [name]')


class DoitRichReporter():
    desc = 'Rich color reporter'

    def __init__(self, console: Console, options=None):
        self.console = console
        columns = [
            "[progress.description]{task.description}",
            TimeElapsedColumn(),
            BarColumn(),
            "[progress.percentage]{task.completed} / {task.total}",
            "[progress.description]{task.fields[current]}",
        ]
        self.prog_bars = {}
        self.progress = Progress(*columns, console=self.console,
                                 redirect_stdout=False, redirect_stderr=False)


    ########## Progress bar management
    def add_progress_bar(self, description, total):
        # click API calls each progress bar a task
        # Add an extra field that contains the detail of the item (doit-task name)
        self.prog_bars[description] = self.progress.add_task(
            description, total=total, current=None)

    def update_progress(self, task, **kwargs):
        try:
            base, name = task.name.split(':', 1)
        except ValueError:
            return # ignore group tasks
        if base in self.prog_bars:
            self.progress.update(self.prog_bars[base], current=name, **kwargs)
    ###############################


    def initialize(self, tasks, selected_tasks):
        """called just after tasks have been loaded before execution starts"""
        # console.print(Panel(str(tasks), title="tasks"))
        # console.print(Panel(str(selected_tasks), title="selected"))
        self.progress.start()

    def get_status(self, task):
        self.update_progress(task)

    def execute_task(self, task):
        pass

    def skip_uptodate(self, task):
        self.update_progress(task, advance=1)

    def skip_ignore(self, task):
        self.update_progress(task, advance=1)

    def add_failure(self, task, exception):
        if task.subtask_of:
            self.update_progress(task, advance=1)
        if not isinstance(exception, DoitTaskFailed):
            self.console.print(Panel(str(exception), title="Error"))

    def add_success(self, task):
        self.update_progress(task, advance=1)

    def complete_run(self):
        self.progress.stop()

    def cleanup_error(self, exception):
        raise NotImplementedError()

    def runtime_error(self, msg):
        self.console.print(Panel(msg, title="Error"))

    def teardown_task(self, task):
        """called when starts the execution of teardown action"""
        pass


class FlakeRichReporter(FlakeReporter):
    def __init__(self, console):
        self.print = console.print

    def flake(self, msg):
        text = msg.message % msg.message_args
        self.print(f'{msg.filename}:{msg.lineno}:{msg.col+1} {text}')

    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax error in C{filename}.

        @param filename: The path to the file with the syntax error.
        @ptype filename: C{unicode}
        @param msg: An explanation of the syntax error.
        @ptype msg: C{unicode}
        @param lineno: The line number where the syntax error occurred.
        @ptype lineno: C{int}
        @param offset: The column on which the syntax error occurred, or None.
        @ptype offset: C{int}
        @param text: The source code containing the syntax error.
        @ptype text: C{unicode}
        """
        line = text.splitlines()[-1]
        if offset is not None:
            error = '%s:%d:%d: %s' % (filename, lineno, offset, msg)
        else:
            error = '%s:%d: %s' % (filename, lineno, msg)
        if offset is not None:
            caret = re.sub(r'\S', ' ', line[:offset - 1])
        self.print(Panel(f'{error}\n{line}\n{caret}^', title="Syntax Error"))


class CodeStyleRichReporter(pycodestyle.BaseReport):
    console = None # must be assigned after creation

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = text[:4]
        if self._ignore_code(code):
            return
        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1
            self.messages[code] = text[5:]
        # Don't care about expected errors or warnings
        if code in self.expected:
            return
        if self.print_filename and not self.file_errors:
            print(self.filename)
        self.file_errors += 1
        self.total_errors += 1
        return code




##################################################################
### helper to create doit tasks

class Linter():
    """pyflakes + pycodestyle"""
    def __init__(self, console, config_file=None):
        style = pycodestyle.StyleGuide(config_file=config_file)
        style_reporter = style.init_report(CodeStyleRichReporter)
        style_reporter.console = console
        self.style = style
        self.flake_reporter = FlakeRichReporter(console)

    def __call__(self, fn):
        """execute pyflakes and pycodestyle on single file"""
        flake_result = checkPath(fn, reporter=self.flake_reporter)
        style_result = self.style.input_file(fn)
        return flake_result==0 and style_result==0
