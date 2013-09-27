=======
FAQ
=======

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
