"""this is a plugin/hook for bazaar. just add this file to ~/.bazaar/plugins/

The MIT License
Copyright (c) 2008 Eduardo Naufel Schettino
see LICENSE 
"""

from bzrlib import branch

def pre_commit_hook(local, master, old_revno, old_revid, future_revno, future_revid, tree_delta, future_tree):
    """This hook will execute precommit script from root path of the bazaar
    branch. Commit will be canceled if precommit fails."""

    import os,subprocess
    from bzrlib import errors

    # this hook only makes sense if a precommit file exist.
    if not os.path.exists("precommit"):
        return
    try:
        subprocess.check_call(os.path.abspath("precommit"))
    # if precommit fails (process return not zero) cancel commit.
    except subprocess.CalledProcessError:
        raise errors.BzrError("pre commit check failed.")

  
branch.Branch.hooks.install_hook('pre_commit', pre_commit_hook)
branch.Branch.hooks.name_hook(pre_commit_hook, 'Check pre_commit hook')
