"""generate shell script with tab complention code for doit commands/tasks"""

import sys
from string import Template

from .cmd_base import DoitCmdBase


opt_hardcode_tasks = {
    'name': 'hardcode_tasks',
    'short': '',
    'long': 'hardcode-tasks',
    'type': bool,
    'default': False,
    'help': 'Hardcode tasks from current task list.',
    }


# Variables starting with 'pt_' belongs to the Python Template
# to generate the script.
# Remaining are shell variables used in the script.
bash_start = """# bash completion for $pt_bin_name
# auto-generate by `$pt_bin_name tabcomplention`

# to activate it you need to 'source' the generate script
# $ source <generated-script>

# reference => http://www.debian-administration.org/articles/317
# patch => http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=711879

_$pt_bin_name()
{
    local cur prev words cword basetask sub_cmds tasks i dodof
    COMPREPLY=()
    # remove colon from word separator list because doit uses colon on task names
    _get_comp_words_by_ref -n : cur prev words cword
    # list of sub-commands
    sub_cmds="$pt_cmds"

"""


bash_opt_file = """
    # options that take file/dir as values should complete file-system
    if [[ "$prev" == "-f" || "$prev" == "-d" || "$prev" == "-o" ]]; then
        _filedir
        return 0
    fi
    if [[ "$cur" == *=* ]]; then
        prev=${cur/=*/}
        cur=${cur/*=/}
        if [[ "$prev" == "--file=" || "$prev" == "--dir=" || "$prev" == "--output-file=" ]]; then
            _filedir -o nospace
            return 0
        fi
    fi

"""


bash_get_dodo = """
    # get name of the dodo file
    for (( i=0; i < ${#words[@]}; i++)); do
        case "${words[i]}" in
        -f)
            dodof=${words[i+1]}
            break
            ;;
        --file=*)
            dodof=${words[i]/*=/}
            break
            ;;
        esac
    done
    # dodo file not specified, use default
    if [ ! $dodof ]
      then
         dodof="dodo.py"
    fi

"""

bash_task_list = """
    # get task list
    # if it there is colon it is getting a subtask...
    if [[ "$cur" == *:* ]]; then
        # extract base task name (remove everything after colon)
        basetask=${cur%:*}
        # sub-tasks
        tasks=$($pt_bin_name list $pt_list_param --quiet --all ${basetask} 2>/dev/null)
        COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )
        __ltrim_colon_completions "$cur"
        return 0
    # without colons get only top tasks
    else
        tasks=$pt_tasks
    fi

"""

bash_end = """
    # match for first parameter must be sub-command or task
    # FIXME doit accepts options "-" in the first parameter but we ignore this case
    if [[ ${cword} == 1 ]] ; then
        COMPREPLY=( $(compgen -W "${sub_cmds} ${tasks}" -- ${cur}) )
        return 0
    fi

    # if there is already one parameter match only tasks (no commands)
    COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )

}
complete -F _$pt_bin_name $pt_bin_name
"""


class TabCompletion(DoitCmdBase):
    """generate scripts for tab-completion"""
    doc_purpose = "generate script for tab-complention"
    doc_usage = ""
    doc_description = None

    cmd_options = (opt_hardcode_tasks, )

    def execute(self, opt_values, pos_args):
        # some applications built with doit do not use dodo.py files
        for opt in self.options:
            if opt.name=='dodoFile':
                get_dodo_part = bash_get_dodo
                pt_list_param = '--file="$dodof"'
                break
        else:
            get_dodo_part = ''
            pt_list_param = ''


        template_vars = {
            'pt_bin_name': sys.argv[0].split('/')[-1],
            'pt_cmds': ' '.join(self.doit_app.sub_cmds),
            'pt_list_param': pt_list_param,
            }

        if opt_values['hardcode_tasks']:
            self.task_list, self.config = self._loader.load_tasks(
                self, opt_values, pos_args)
            template_vars['pt_tasks'] = '"{}"'.format(
                ' '.join(t.name for t in self.task_list if not t.is_subtask))
        else:
            tmpl_tasks = Template("$($pt_bin_name list $pt_list_param --quiet 2>/dev/null)")
            template_vars['pt_tasks'] = tmpl_tasks.safe_substitute(template_vars)

        template = Template(bash_start + bash_opt_file + get_dodo_part +
                            bash_task_list + bash_end)
        self.outstream.write(template.safe_substitute(template_vars))
