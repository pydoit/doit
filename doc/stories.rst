.. meta::
   :description: pydoit Success Stories on scientific pipelines, build system, content generation and DevOps
   :keywords: python, doit, case study, build system, content generation, devops, scientific pipelines

.. title:: pydoit Success Stories: users testimonials


Success Stories
===============

Do you have a success story? Please share it!

Send a pull-request on github describing your project, how `doit` is used,
and why `doit` was chosen.


.. contents::
   :local:



Scientific
----------


Biomechanics Lab / Stanford University, USA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Christopher Dembia <http://chrisdembia.github.io>`_ (2014-04-03)


I am a graduate student in a biomechanics lab that studies how humans coordinate
their muscles in movements like walking or running.
We record someone's motion using reflective motion capture markers and by
recording the force their feet exert on the ground.
We put this data into our software, which gives back an estimate of the
force each muscle (92 muscles) was generating throughout the observed motion.
In a typical study, we record about 100 walking motions.
To analyze a single walking motion, we need to run 4 different executables in
sequence.
Each executable requires a handful of input files, and generates a
handful of output files that a subsequent executable uses as input.

So, a study entails about 1000 files, some of which contain raw data, but most
of which are intermediate files (output of one executable and input to another
executable).
Typically, a researcher manages this workflow manually.
However, that is prone to error,
as a researcher may forget to properly modify all
relevant files if an error is noticed in, for example, a raw data file.

With `doit`, I am automating this workflow for my current study.
This allows me to avoid errors and avoid unnecessary duplication of files.
Most importantly, if I learn that I must modify something in a file
that is an input toward the beginning of this workflow,
`doit` will allow me to automatically update all my
results without missing a step.

I tried to do this with `Make` first.
`Make` just was not made to do what I want.
Also, my lab's software has python bindings, so my entire workflow can be
in python.
Also, the ability to script anything directly into the workflow is
important, and `Make` can't do that.
`CMake` was another option, but that's not general enough.
`doit` is just completely generic, and the interface is simple yet very flexible.



`Computational Metagenomics Lab <http://cibiocm.bitbucket.org>`_ / University of Trento, Italy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Nicola Segata <http://cibiocm.bitbucket.org>`_ (2015-01-20)

My laboratory of Computational Metagenomics at University of Trento studies the
human microbiome, i.e. the huge microbial diversity populating our body.

Our analyses involve processing several thousands of microbial genomes (long
sequences of DNA) with a series of computational steps (mostly written in
python) on subset of those genomes.  Genomes are organized in a hierarchical
structure (the taxonomy) and many steps of our pipelines need to take into
account these dependencies.

`doit` is just the right way to do this. We actually even tried to implement
something like this on our own, but we are now switching to `doit` because it
has all the features we need and it is intuitive to use. We particularly love
the possibility of specifying dependencies "on the fly".

We are now thinking to convert all our pipelines to the `doit` format. Given the
importance of `doit` for our research and its potential for bioinformatic
pipelines we are happy to support this project scientifically (by citing it in
our papers, mentioning it in our funding requests, etc).

Thanks for developing `doit`, it's just wonderful for computational biology (and
for many other tasks, of course, but this is our research field:)!

`Cheminformatics data processing @ Atomwise <https://www.atomwise.com>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Jon Sorenson <https://github.com/drkeoni>`_ (2018-12-14)

I came to `doit` from the loose requirement that I wanted a task-dependency/DAG type
of workflow solution for the various pipelines that our team is constructing.
I come from computational biology originally, and the similarity of data processing pipelines
to build systems has long been appreciated.  More than a decade ago
many of us were writing bioinformatics
pipelines in `make` because it gave us so many features "for free."

Starting afresh at `Atomwise <https://www.atomwise.com/>`_ I did a survey of what DAG-based workflow
execution frameworks were out there---restricting my search to `python`, active
maintenance, good documentation etc.  Besides `doit` I evaluated `bonobo`, `Luigi`, and `airflow`.
`bonobo` didn't fit my needs for dependency-based processing.  `Luigi` and `airflow` are
very nice, but I didn't have any particular need for distributed workflows and the
heavier weight feel of these platforms.  My favorite experience was `airflow` but it
didn't have (obvious) support for re-entrant processing: running a pipeline
from an intermediate stage.

I knew that build-system based frameworks would do exactly what I wanted and not
hand me too much cruft, and on that note I found `doit`.  It's worked perfectly
for my needs:

- The order of tasks is derived from dependencies

- Tasks can be executed in parallel if they don't depend on each other

- Plenty of bells and whistles to relieve the pipeline developer from writing
  boilerplate code (easy task documentation, discovery of the pipeline state,
  easy process for re-doing tasks)

- Very light-weight. In this sense `doit` is the perfect example of a UNIX-style
  tool: *do one thing and do it well*.  `Luigi` and `airflow` are
  attractive, but they also suffer from kitchen-sink bloat.  If you simply
  want a pythonic alternative to `Makefiles` or `bash` scripts, `doit`
  is great solution.

- It's easy to build up a library of common tasks that can be reused by
  multiple `doit` pipelines.


Build System
------------

`BMW <https://www.bmw.com/de/index.html>`_ (Automotive)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Mike Pagel <https://github.com/moltob>`_ (2019-02-06)

We are responsible for the development of the next generation instrument
cluster software at BMW. While we use CMake for the actual build of libraries
and applications, we have learned in the past that you *can* do almost everything
with ``CMake``, but probably you *shouldn’t*.

``CMake`` is optimized for all tasks around compiler toolchain control, but the
language is somewhat special and functions and macros cannot easily be tested
outside of a real build. This is where ``doit`` enters the stage: We use it for
everything *but* compiling software, as a high level command line interface for
the development teams (and the CI systems). These are some of the tasks we
perform with ``doit``:

- Downloading and installing tools.
- Calling ``CMake`` for multiple compiler toolchains.
- Driving various code analysis tools.
- Reporting.
- Packaging the software for later deployment to the car etc.
- Checking if dependencies of the toolchain are outdated and creating automatic
  pull requests.

Basically we implemented our complete high-level build control in ``doit``. The
resulting framework is now used by us and our suppliers and supports a team
over 100 developers. Since ``doit`` is written in Python, we have professional test
frameworks, linters and code analyzers at hand, allowing for a thoroughly
tested and well-designed platform for our build-systems and automation.


Game Development
^^^^^^^^^^^^^^^^

by `@FrankStain <https://github.com/pydoit/doit/issues/207#issuecomment-333367177>`_ (2017-10-01)

I'm professional game developer. Also, i support my own huge game framework written on C++. :)

So, the large scalable build systems are the game building automation tools. It consists of game binary image builders for different platforms, including cross-compilation of source code and source code generation from some DSL schemes. Also it consists of resource generators, where a lot of resource types (dozens of types: textures, 3d objects and scene graphs, sounds, database and state machine raw data) have to pass through dozens of compilation steps. After all, such build system consists of dynamic testing tool, which makes some tests on build target before make it published for Draft usage, QA or Retail customers. And, yep, publishing/QA deployment also implemented as part of build system.

Just imagine you need to read PNG into pixelmap, compress it into ETC2, ATCI, S3-TC5/BC3 and PVR-TC4, after what each of compressed texture should be placed into different resource pack, obfuscated and encrypted. And all is done by different tasks, because i can read textures even from database, zip-file or other pack and may not wish to compress it into some formats.
Each sound should be loaded from PCM, converted into MP3 or OGG and linked with each sound mixer where it used, after what it also have to be placed at proper resource pack, obfuscated and encrypted.
3d location compilation process is about two hundreds tasks on just objects, not files. It's most complex resource pipeline in build system.

`doit` is well designed tool for such purposes, i think.


`MetalK8s @ Scality <https://www.scality.com/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Sylvain Laperche <https://github.com/slaperche-scality>`_ (2019-05-06)

We use ``doit`` as the build system for
`MetalK8s <https://github.com/scality/metalk8s/>`_, a Kubernetes distribution
with a focus on long-term on-prem deployments.

``doit``'s main role is to generate the MetalK8s ISO archive that should contain
everything to allow offline installation and deployment of a Kubernetes cluster.
This involves several tasks like downloading and/or building container images,
building software packages (RPMs) from source, creating packages repositories, …
We also use ``doit`` for others tasks, such as executing linting tools and
spawning a local cluster using Vagrant.

We wanted to move away from ``make`` because as complexity grows it becomes hard
to maintain, evolve and debug.
Given that almost everyone in our team is familiar with Python, we started to
look for alternatives that are Python-based.

We investigated ``Scons``, ``waf``, ``Invoke`` and ``doit``.
``Scons`` and ``waf`` were put aside because their main advantage is to hide the
underlying complexity of compiling software in a portable way (which we aren't
doing). However, running arbitrary shell commands was cumbersome.
``Invoke`` was pretty good at executing commands, but didn't have a good
dependency tracking system: a task will always be re-executed even if its
dependencies are unchanged, which was a deal-breaker.

``doit`` was chosen to replace our ``make``-based approach because of the
following characteristics:

- Easy to invoke external commands
- Simple and flexible core concepts
- Easily customizable (``uptodate`` API, ``clean`` attribute, …)
- Extensive documentation
- Actively maintained
- Various useful features: JSON output, ``doit info`` to inspect dependencies,
  ``doit auto`` for automatically replaying tasks based on dependency changes…


Content Generation
------------------


Nikola
^^^^^^

by `the Nikola team <https://getnikola.com/>`_

`Nikola <https://getnikola.com/>`_ is a Static Site and Blog Generator.  `doit`
is used to process all the tasks required for building the website (HTML files,
indexes, RSS, copying files…).  Use of `doit` makes Nikola unique: unlike other
static site generators, Nikola regenerates only the files that were changed
since last build (and not all files in the site!).  ``nikola build``, the
centerpiece of Nikola, is basically the usual ``doit run`` command.

`doit` is what makes Nikola extremely fast, even for large sites.  Only a handful
of files actually *change* on a rebuild.  Using the dependency architecture of
`doit` (for files and configuration), we are able to rebuild only what is needed.

Nikola is an `open-source <https://github.com/getnikola/nikola>`_ project with
many users and contributors.


Document Production
^^^^^^^^^^^^^^^^^^^

(2018-02-01)

`Carve Systems <https://carvesystems.com>`_ uses `doit` as the core automation tool
for all of our document production. This customized tool based on Pandoc, Latex, and
coordinated by `doit` is used by everyone in our company to prepare our primary
customer facing deliverable. Previously we used Makefiles to coordinate builds. `doit`
let us create a system that can be more easily maintained, tested, and extended using
plugins.




DevOps
------


University of Oslo Library, Norway
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by_ `Dan Michael O. Heggø <https://github.com/danmichaelo>`_ (2018-02-26)

.. _by: #https-data-ub-uio-no

We are using `doit` for the publishing workflow at our vocabulary server https://data.ub.uio.no/ .
The server checks multiple remote sources for changes, and when there’s new changes somewhere, the data is fetched,
converted to different formats, published and pushed to Fuseki and Elasticsearch.

One part I love about `doit` is that you can control what is considered a change.
For remote files, I have created a task that checks if some header, like ETag or Last-Modified, has changed.
If it has not, I set `uptodate` to True and stop there.

Another part I love is the ability to re-use tasks.
Each vocabulary (like https://github.com/realfagstermer/realfagstermer and https://github.com/scriptotek/humord)
has a different publication workflow, but many tasks are shared.
With `doit`, I have created a collection of tasks and task generators (https://github.com/scriptotek/data_ub_tasks/)
that I use with all the vocabularies.

Finally, it's great that you can mix shell commands and Python tasks so easily.
This cuts development time and makes the move from using Makefiles much easier.
