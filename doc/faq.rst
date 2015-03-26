=======
FAQ
=======


Why is `doit` written in all lowercase instead of CamelCase?
-------------------------------------------------------------

At first it would be written in CamelCase `DoIt` but depending on the font
some people would read it as `dolt <http://en.wiktionary.org/wiki/dolt#Noun>`_
with an `L` instead of `I`. So I just set it as lowercase to avoid confusion.


*doit* is too verbose, why don't you use decorators?
-----------------------------------------------------

`doit` is designed to be extensible.
A simple dictionary is actually the most flexible representation.
It is possible to create different interfaces on top of it.
Check this `blog post <http://blog.schettino72.net/posts/doit-task-creation.html>`_
for some examples.


`dodo.py` file itself should be a `file_dep` for all tasks
-----------------------------------------------------------

  If I edit my `dodo.py` file and re-run *doit*,
  and my tasks are otherwise up-to-date, the modified tasks are not re-run.

While developing your tasks it is recommended
to use ``doit forget`` after you change your tasks
or use ``doit --always-run``.

In case you really want, you will need to explicitly
add the `dodo.py` in `file_dep` of your tasks manually.

If `dodo.py` was an implicit `file_dep`:

 * how would you disable it?
 * should imported files from your `dodo.py` also be a `file_dep`?


Why `file_dep` can not depend on a directory/folder?
------------------------------------------------------

A `file_dep` is considered to not be up-to-date when the content of
the file changes. But what is a folder change?
Some people expect it to be a change in any of its containing files
(for this case see question below).
Others expect it to be whether the folder exist or not,
or if a new file was added or removed from the folder (for these
cases you should implement a custom ``uptodate``
(:ref:`check the API<uptodate_api>`).


How to make a dependency on all files in a folder?
----------------------------------------------------

``file_dep`` does NOT support folders.
If you want to specify all files from a folder you can use a third
party library like `pathlib <https://pypi.python.org/pypi/pathlib>`_ (
`pathlib` was add on python's 3.4 stdlib).
