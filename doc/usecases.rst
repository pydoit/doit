.. meta::
   :description: pydoit is a generic tool based on build-tool concepts. Flexible and scalable.
   :keywords: python, doit, CLI, linux, windows, task-runner, build-tool, pipeline, workflow, incremental build, data pipeline

.. title:: pydoit use cases - from CLI task-runner to complex pipelines

=========
Use Cases
=========

Here are some use cases, where `doit` can help you with automation of your tasks.



Simplify cumbersome command line calls
======================================

Do you have to repeatedly call complex command like this?

.. code-block:: console

    $ aws s3 sync _built/html s3://buck/et --exclude "*" --include "*.html"


Wrap it into `dodo.py` file:

.. code-block:: python

    def task_publish():
      """Publish to AWS S3"""
      return {
        "actions": [
            'aws s3 sync _built/html s3://buck/et --exclude "*" --include "*.html"'
        ]
      }

and next time just:

.. code-block:: console

    $ doit publish

It is easy to include multiple actions into one task or use multiple tasks.


Automate typical project related actions
========================================

Do you have to lint your code, run test suite, evaluate coverage,
generate documentation incl. spelling?

Create the `dodo.py`, which defines tasks you have to do and next time:

.. code-block:: console

    $ doit list
    coverage          show coverage for all modules including tests
    coverage_module   show coverage for individual modules
    coverage_src      show coverage for all modules (exclude tests)
    package           create/upload package to pypi
    pyflakes          
    pypi              create/upload package to pypi
    spell             spell checker for doc files
    sphinx            build sphinx docs
    tutorial_check    check tutorial sample are at least runnable without error
    ut                run unit-tests
    website           dodo file create website html files
    website_update    update website on SITE_PATH

and then decide which task to run:

.. code-block:: console

    $ doit spell

Share unified way of doing things
=================================

Do you expect your colleagues perform the same steps before committing
changes to repository? What to do with the complains the steps are too complex?

Provide them with the `dodo.py` file doing the things. What goes easy,
is more likely to be used.

`dodo.py` will become easy to use prescription of best practices.

Optimize processing time by skipping tasks already done
=======================================================

You dump your database and convert the data to CSV. It takes minutes,
but often the input is the same as before. Why to do things already
done and wait?

Wrap the conversion into `doit` task and `doit` will automatically
detect, the input and output are already in sync and complete in
fraction of a second, when possible.

Manage complex set of depending tasks
=====================================

The system you code shall do many small actions, which are interdependent.

Split it into small tasks, define (file) dependencies and let `doit`
do the planning of what shall be processed first and what next.

Your solution will be clean and modular.

Speed up by parallel task execution
===================================
You already have bunch of tasks defined, results are correct, it only takes so
much time. But wait, you have multi-core machine!

Just ask for parallel processing:

.. code-block:: console

   $ doit -n 4

and `doit` will take care of planning and make all your CPU cores hot.

No need to rewrite your processing from scratch, properly declared tasks is all
what you have to provide.

Extend your project by doit features
====================================
Your own python project would need features of `doit`, but you cannot ask your users to call `doit` on command line?

Simply integrate `doit` functionality into your own command line tool and nobody will notice where it comes from.

Create cross-platform tool for processing  your stuff
=====================================================
Do you have team members working on MS Windows and others on Linux?

Scripts are great, but all those small shell differences prevent
single reusable solution.

With `dodo.py` and python you are more likely to write the processing
in cross-platform way. Use `pathlib.Path` and `shutils` magic to
create directories, move files around, copy them, etc.
