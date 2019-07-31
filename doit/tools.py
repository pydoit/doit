"""extra goodies to be used in dodo files"""

import os
import time as time_module
import datetime
import json
import hashlib
import operator
import subprocess
from collections import namedtuple
from pathlib import PurePath, Path

from . import exceptions
from .action import CmdAction, PythonAction
from .task import result_dep # imported for backward compatibility
result_dep # pyflakes

# action
def create_folder(dir_path):
    """create a folder in the given path if it doesnt exist yet."""
    os.makedirs(dir_path, exist_ok=True)


# title
def title_with_actions(task):
    """return task name task actions"""
    if task.actions:
        title = "\n\t".join([str(action) for action in task.actions])
    # A task that contains no actions at all
    # is used as group task
    else:
        title = "Group: %s" % ", ".join(task.task_dep)
    return "%s => %s"% (task.name, title)



# uptodate
def run_once(task, values):
    """execute task just once
    used when user manually manages a dependency
    """
    def save_executed():
        return {'run-once': True}
    task.value_savers.append(save_executed)
    return values.get('run-once', False)



# uptodate
class config_changed(object):
    """check if passed config was modified
    @var config (str) or (dict)
    @var encoder (json.JSONEncoder) Encoder used to convert non-default values.
    """
    def __init__(self, config, encoder=None):
        self.config = config
        self.config_digest = None
        self.encoder = encoder

    def _calc_digest(self):
        if isinstance(self.config, str):
            return self.config
        elif isinstance(self.config, dict):
            data = json.dumps(self.config, sort_keys=True, cls=self.encoder)
            byte_data = data.encode("utf-8")
            return hashlib.md5(byte_data).hexdigest()
        else:
            raise Exception(('Invalid type of config_changed parameter got %s' +
                             ', must be string or dict') % (type(self.config),))

    def configure_task(self, task):
        task.value_savers.append(lambda: {'_config_changed':self.config_digest})

    def __call__(self, task, values):
        """return True if config values are UNCHANGED"""
        self.config_digest = self._calc_digest()
        last_success = values.get('_config_changed')
        if last_success is None:
            return False
        return (last_success == self.config_digest)



# uptodate
class timeout(object):
    """add timeout to task

    @param timeout_limit: (datetime.timedelta, int) in seconds

    if the time elapsed since last time task was executed is bigger than
    the "timeout" time the task is NOT up-to-date
    """

    def __init__(self, timeout_limit):
        if isinstance(timeout_limit, datetime.timedelta):
            self.limit_sec = ((timeout_limit.days * 24 * 3600) +
                              timeout_limit.seconds)
        elif isinstance(timeout_limit, int):
            self.limit_sec = timeout_limit
        else:
            msg = "timeout should be datetime.timedelta or int got %r "
            raise Exception(msg % timeout_limit)

    def __call__(self, task, values):
        def save_now():
            return {'success-time': time_module.time()}
        task.value_savers.append(save_now)
        last_success = values.get('success-time', None)
        if last_success is None:
            return False
        return (time_module.time() - last_success) < self.limit_sec



# uptodate
class check_timestamp_unchanged(object):
    """check if timestamp of a given file/dir is unchanged since last run.

    The C{cmp_op} parameter can be used to customize when timestamps are
    considered unchanged, e.g. you could pass L{operator.ge} to also consider
    e.g. files reverted to an older copy as unchanged; or pass a custom
    function to completely customize what unchanged means.

    If the specified file does not exist, an exception will be raised.  Note
    that if the file C{fn} is a target of another task you should probably add
    C{task_dep} on that task to ensure the file is created before checking it.
    """
    def __init__(self, file_name, time='mtime', cmp_op=operator.eq):
        """initialize the callable

        @param fn: (str) path to file/directory to check
        @param time: (str) which timestamp field to check, can be one of
                     (atime, access, ctime, status, mtime, modify)
        @param cmp_op: (callable) takes two parameters (prev_time, current_time)
                   should return True if the timestamp is considered unchanged

        @raises ValueError: if invalid C{time} value is passed
        """
        if time in ('atime', 'access'):
            self._timeattr = 'st_atime'
        elif time in ('ctime', 'status'):
            self._timeattr = 'st_ctime'
        elif time in ('mtime', 'modify'):
            self._timeattr = 'st_mtime'
        else:
            raise ValueError('time can be one of: atime, access, ctime, '
                             'status, mtime, modify (got: %r)' % time)
        self._file_name = file_name
        self._cmp_op = cmp_op
        self._key = '.'.join([self._file_name, self._timeattr])

    def _get_time(self):
        return getattr(os.stat(self._file_name), self._timeattr)

    def __call__(self, task, values):
        """register action that saves the timestamp and check current timestamp

        @raises OSError: if cannot stat C{self._file_name} file
                         (e.g. doesn't exist)
        """
        def save_now():
            return {self._key: self._get_time()}
        task.value_savers.append(save_now)

        prev_time = values.get(self._key)
        if prev_time is None: # this is first run
            return False
        current_time = self._get_time()
        return self._cmp_op(prev_time, current_time)


# action class
class LongRunning(CmdAction):
    """Action to handle a Long running shell process,
    usually a server or service.
    Properties:

        * the output is never captured
        * it is always successful (return code is not used)
        * "swallow" KeyboardInterrupt
    """
    def execute(self, out=None, err=None):
        action = self.expand_action()
        process = subprocess.Popen(action, shell=self.shell, **self.pkwargs)
        try:
            process.wait()
        except KeyboardInterrupt:
            # normal way to stop interactive process
            pass

# the name InteractiveAction is deprecated on 0.25
InteractiveAction = LongRunning


class Interactive(CmdAction):
    """Action to handle Interactive shell process:

       * the output is never captured
    """
    def execute(self, out=None, err=None):
        action = self.expand_action()
        process = subprocess.Popen(action, shell=self.shell, **self.pkwargs)
        process.wait()
        if process.returncode != 0:
            return exceptions.TaskFailed(
                "Interactive command failed: '%s' returned %s" %
                (action, process.returncode))



# action class
class PythonInteractiveAction(PythonAction):
    """Action to handle Interactive python:

       * the output is never captured
       * it is successful unless a exception is raised
    """
    def execute(self, out=None, err=None):
        kwargs = self._prepare_kwargs()
        try:
            returned_value = self.py_callable(*self.args, **kwargs)
        except Exception as exception:
            return exceptions.TaskError("PythonAction Error", exception)
        if isinstance(returned_value, str):
            self.result = returned_value
        elif isinstance(returned_value, dict):
            self.values = returned_value
            self.result = returned_value


# debug helper
def set_trace(): # pragma: no cover
    """start debugger, make sure stdout shows pdb output.
    output is not restored.
    """
    import pdb
    import sys
    debugger = pdb.Pdb(stdin=sys.__stdin__, stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back) #pylint: disable=W0212



def load_ipython_extension(ip=None):  # pragma: no cover
    """
    Defines a ``%doit`` magic function[1] that discovers and execute tasks
    from IPython's interactive variables (global namespace).

    It will fail if not invoked from within an interactive IPython shell.

    .. Tip::
        To permanently add this magic-function to your IPython, create a new
        script inside your startup-profile
        (``~/.ipython/profile_default/startup/doit_magic.ipy``) with the
        following content:

            %load_ext doit
            %reload_ext doit
            %doit list

    [1] http://ipython.org/ipython-doc/dev/interactive/tutorial.html#magic-functions
    """
    from IPython.core.getipython import get_ipython
    from IPython.core.magic import register_line_magic

    from doit.cmd_base import ModuleTaskLoader
    from doit.doit_cmd import DoitMain

    # Only (re)load_ext provides the ip context.
    ip = ip or get_ipython()

    @register_line_magic
    def doit(line):
        """
        Run *doit* with `task_creators` from all interactive variables
        (IPython's global namespace).

        Examples:

            >>> %doit --help          ## Show help for options and arguments.

            >>> def task_foo():
                    return {'actions': ['echo hi IPython'],
                            'verbosity': 2}

            >>> %doit list            ## List any tasks discovered.
            foo

            >>> %doit                 ## Run any tasks.
            .  foo
            hi IPython

        """
        # Override db-files location inside ipython-profile dir,
        # which is certainly writable.
        prof_dir = ip.profile_dir.location
        opt_vals = {'dep_file': os.path.join(prof_dir, 'db', '.doit.db')}
        commander = DoitMain(ModuleTaskLoader(ip.user_module),
                             extra_config={'GLOBAL': opt_vals})
        commander.BIN_NAME = 'doit'
        commander.run(line.split())

# also expose another way of registering ipython extension
register_doit_as_IPython_magic = load_ipython_extension


def gen_matching_files(src_pattern,  # type: Path
                       ):
    """
    Utility generator function used by `file_pattern` to yield of matching file
    elements corresponding to the provided `src_pattern`.

    If `src_pattern` contains a double wildcard `**`, each element returned by
    this generator list will be a tuple containing two elements:

     - the first element is the `Path` of the file or folder that matched the
       search
     - the second element is a string representing the part of the path
       captured by the double wildcard. Otherwise the second element is `None`.

    If no double wildcard `**` is present in `src_pattern`, only path elements
    are yielded.

    :param src_pattern: a `Path` representing the source pattern to match.
        The list returned will contain one item for each file matching
        this pattern, using `glob` to perform the match.
    :return: a generator yielding either <file_path> items, or tuples
        (<file_path>, <captured_double_wildcard_path>) depending on whether a
        `**` was present in the pattern or not.
    """
    # -- validate the source pattern
    src_double_wildcard = None
    src_glob_start = None
    for i, p in enumerate(src_pattern.parts):
        if src_glob_start is None and ('*' in p or '?' in p or '[' in p):
            src_glob_start = i
        if '**' in p:
            if p != '**':
                raise ValueError("Invalid pattern '%s': double-wildcard should"
                                 " be alone in its path element" % src_pattern)
            elif src_double_wildcard is None:
                try:
                    end_ptrn = Path(*src_pattern.parts[i+1:])
                except IndexError:
                    end_ptrn = None
                src_double_wildcard = (i, end_ptrn)
            else:
                raise ValueError("Invalid source pattern '%s': several "
                                 "double-wildcards exist." % src_pattern)

    # -- Perform the glob file search operation, using Pathlib.glob
    if src_glob_start is None:
        glob_results = (src_pattern,)
    else:
        root_path = src_pattern.parents[len(src_pattern.parts)
                                        - src_glob_start - 1]
        to_search = PurePath(*src_pattern.parts[src_glob_start:])
        glob_results = root_path.glob(str(to_search))

    # Create the appropriate generator according to presence of '**'
    if src_double_wildcard is None:
        # simply yield the matching file Path items
        for matched_file in glob_results:
            yield matched_file
    else:
        # for each matching item, find the path captured by the '**' and yield
        for matched_file in glob_results:
            # get information about the double wildcard
            src_dblwildcard_idx, src_ptrn_suffix = src_double_wildcard

            # split the path in two according to the double wildcard position
            root_path = matched_file.parents[len(matched_file.parts)
                                              - src_dblwildcard_idx - 1]
            variable_path = matched_file.parts[src_dblwildcard_idx:]

            # remove the end of the path according to what was really matched
            if src_ptrn_suffix is not None:
                src_ptrn_suffix_str = str(src_ptrn_suffix)
                for i in range(len(variable_path)):
                    s_root = (root_path / Path(*variable_path[:i]))
                    if matched_file in tuple(s_root.glob(src_ptrn_suffix_str)):
                        variable_path = variable_path[:i]
                        break
                else:
                    # nothing matched, this has to be because len is 0.
                    assert len(variable_path) == 0

            yield (matched_file, str(PurePath(*variable_path)))


class FileItem(namedtuple('FileItem',
                          ('src_path', 'has_multi_targets', 'dst_path'))):
    """
    Represents an item created by `file_pattern(...)`.
    """
    def __getattr__(self, item):
        """
        If the item has multiple targets, allow users to access them with an
        attribute style. (see `munch` for inspiration)
        """
        if self.has_multi_targets:
            try:
                return self.dst_path[item]
            except KeyError as e:
                raise AttributeError(item)
        else:
            return super(FileItem, self).__getattribute__(item)

    def __str__(self):
        if self.has_multi_targets:
            secnd_str = "{%s}" % ', '.join(["%s=%s" % (k, v.as_posix())
                                            for k, v in self.dst_path.items()])
        else:
            secnd_str = self.dst_path.as_posix()

        return "%s -> %s" % (self.src_path.as_posix(), secnd_str)


def file_pattern(src_pattern,  # type: Union[str, Any]
                 dst_pattern   # type: Union[str, Any]
                 ):
    # type: (...) -> List[FileItem]
    """
    Lists all source files corresponding to `src_pattern` and creates target
    file paths according to `dst_pattern`. The result is a list of `FileItem`
    objects containing both the source and destination paths, that can
    typically be used as "to-do lists" in task generators as shown in the
    example below:

    ```python
    from doit.tools import file_pattern

    ALL_DATA = file_pattern('./data/defs/**/*.ddl', './data/raw/%.csv')

    def task_download_data():
        '''
        Downloads csv file `./data/raw/<dataset>.csv`
        for each def file `./data/defs/**/<dataset>.ddl`.
        '''
        for data in ALL_DATA:
            yield {
                'name': data.name,
                'file_dep': [data.src_path, DATA_DDL_PYSCRIPT],
                'actions': ["python %s --ddl_csv %s"
                            % (DATA_DDL_PYSCRIPT, data.src_path)],
                'verbosity': 2,
                'targets': [data.dst_path]
            }
    ```

    `src_pattern` and `dst_pattern` patterns can be a string or any object - in
    which case `str()` will be applied on the object before use. For example
    you can use `Path` instances from `pathlib`.

    Source pattern `src_pattern` should follow the python `glob` syntax,
    see https://docs.python.org/3/library/glob.html.

    Destination pattern `dst_pattern` represents target paths to create. In
    this pattern, the following special expressions can be used:

     - *stem* character `%`: will be replaced with the stem of a matched file
       or the folder name of a matched folder.

     - *variable path* characters `%%`: represents the part of the path matched
       by the `**` in the source pattern. In that case the source pattern MUST
       contain a double-wildcard, and only one.

    It is possible to declare multiple destination patterns by passing a `dict`
    `dst_pattern` instead of a single element. In that case the resulting list
    will contain `FileItem` instances that have one attribute per pattern.

    This feature was inspired by GNU make 'pattern rules', see
    https://www.gnu.org/software/make/manual/html_node/Pattern-Examples.html

    :param src_pattern: a string or object representing the source pattern to
        match. The list returned will contain one item for each file matching
        this pattern, using `glob` to perform the match.
    :param dst_pattern: a string or object representing the destination
        pattern to use to create target file paths. A dictionary can also be
        provided to create several target file paths at once
    :return: a list of `FileItem` instances with at least two fields `src_path`
        and `dst_path`. When `dst_pattern` is a dictionary, the items will also
        show one attribute per key in that dictionary.
    """
    if not isinstance(src_pattern, PurePath):
        # create a pathlib.Path based on the string view of the object
        # since we will use a parent in this pattern for actual glob search,
        # we use a concrete `Path` not a `PurePath`
        src_pattern_str = str(src_pattern)
        src_has_double_wildcard = '**' in src_pattern_str
        src_pattern = Path(src_pattern_str)
    else:
        src_has_double_wildcard = '**' in str(src_pattern)

    # create the generator
    match_generator = gen_matching_files(src_pattern)

    # -- validate the destination patterns
    def _validate_dst_pattern(dst_pattern):
        """return a validated dst pattern string"""

        # convert the dest pattern
        if not isinstance(dst_pattern, str):
            dst_pattern = str(dst_pattern)

        # validate the dest pattern
        if '*' in dst_pattern:
            raise ValueError("Destination pattern can not contain star '*' "
                             "wildcards, only '%%' characters. Found '%s'"
                             % dst_pattern)
        if '%%' in dst_pattern and not src_has_double_wildcard:
            raise ValueError(
                "Destination pattern '%s' uses a folder path '%%%%' but source"
                " pattern does not include any double-wildcard: '%s'"
                % (dst_pattern, src_pattern))
        return dst_pattern

    try:
        # assume a dictionary of destination patterns
        for dst_name, _dst_pattern in dst_pattern.items():
            dst_pattern[dst_name] = _validate_dst_pattern(_dst_pattern)
        has_multi_targets = True
    except AttributeError:
        # single pattern
        dst_pattern = _validate_dst_pattern(dst_pattern)
        has_multi_targets = False

    res = []
    if not src_has_double_wildcard:
        def _create_dst_path(matching_file, dst_pattern):
            # replace % with stem and convert to Path object
            return Path(dst_pattern.replace('%', matching_file.stem))

        for f_path in match_generator:
            # create the destination path(s)
            if has_multi_targets:
                dst_paths = {dst_name: _create_dst_path(f_path, _dst_pattern)
                             for dst_name, _dst_pattern in dst_pattern.items()}
            else:
                dst_paths = _create_dst_path(f_path, dst_pattern)

            # finally create the container object and append
            item = FileItem(src_path=f_path, dst_path=dst_paths,
                            has_multi_targets=has_multi_targets)
            res.append(item)
    else:
        def _create_dst_path(matching_file, captured_subpath, dst_pattern):
            # replace %% with the **-captured sub-path
            if '%%' in dst_pattern:
                dst_path = dst_pattern.replace('%%', captured_subpath)
            else:
                dst_path = dst_pattern

            # replace % with file stem and convert to Path object
            return Path(dst_path.replace('%', matching_file.stem))

        for f_path, capt_subpath in match_generator:
            # create the destination path(s)
            if has_multi_targets:
                dst_paths = {dst_name: _create_dst_path(f_path, capt_subpath,
                                                        _dst_pattern)
                             for dst_name, _dst_pattern in dst_pattern.items()}
            else:
                dst_paths = _create_dst_path(f_path, capt_subpath, dst_pattern)

            # finally create the container object and append
            item = FileItem(src_path=f_path, dst_path=dst_paths,
                            has_multi_targets=has_multi_targets)
            res.append(item)

    return res
