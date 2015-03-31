# bash completion for doit
# auto-generate by `doit tabcompletion`

# to activate it you need to 'source' the generate script
# $ source <generated-script>

# reference => http://www.debian-administration.org/articles/317
# patch => http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=711879

_doit()
{
    local cur prev words cword basetask sub_cmds tasks i dodof
    COMPREPLY=() # contains list of words with suitable completion
    # remove colon from word separator list because doit uses colon on task names
    _get_comp_words_by_ref -n : cur prev words cword
    # list of sub-commands
    sub_cmds="auto clean dumpdb forget help ignore info list reset-dep run strace tabcompletion"


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


    # get task list
    # if it there is colon it is getting a subtask, complete only subtask names
    if [[ "$cur" == *:* ]]; then
        # extract base task name (remove everything after colon)
        basetask=${cur%:*}
        # sub-tasks
        tasks=$(doit list --file="$dodof" --quiet --all ${basetask} 2>/dev/null)
        COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )
        __ltrim_colon_completions "$cur"
        return 0
    # without colons get only top tasks
    else
        tasks=$(doit list --file="$dodof" --quiet 2>/dev/null)
    fi


    # match for first parameter must be sub-command or task
    # FIXME doit accepts options "-" in the first parameter but we ignore this case
    if [[ ${cword} == 1 ]] ; then
        COMPREPLY=( $(compgen -W "${sub_cmds} ${tasks}" -- ${cur}) )
        return 0
    fi

    case ${words[1]} in

        auto)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        clean)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        dumpdb)
            COMPREPLY=( $(compgen -f -- $cur) )
            return 0
            ;;
        forget)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        help)
            COMPREPLY=( $(compgen -W "${tasks} ${sub_cmds}" -- $cur) )
            return 0
            ;;
        ignore)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        info)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        list)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        reset-dep)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        run)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        strace)
            COMPREPLY=( $(compgen -W "${tasks}" -- $cur) )
            return 0
            ;;
        tabcompletion)
            COMPREPLY=( $(compgen -f -- $cur) )
            return 0
            ;;
    esac

    # if there is already one parameter match only tasks (no commands)
    COMPREPLY=( $(compgen -W "${tasks}" -- ${cur}) )

}
complete -o filenames -F _doit doit
