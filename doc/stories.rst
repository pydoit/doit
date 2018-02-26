

Success Stories
===============

Do you have a success story? Please share it!

Send a pull-request on github describing your project, how `doit` is used,
and why `doit` was chosen.


.. contents::
   :local:



Scientific
----------


Software Carpentry
^^^^^^^^^^^^^^^^^^

The `Software Carpentry Foundation <http://software-carpentry.org>`_ is a
non-profit membership organization devoted to improving basic computing skills
among researchers in science, engineering, medicine, and other disciplines.

`doit` is introduced in the Software Carpentry workshop lesson:
`Automating an analysis pipeline using doit <http://swcarpentry.github.io/bc/intermediate/doit/>`_.



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
`Make` just wasn't made to do what I want.
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



Build System
------------


Game Development
^^^^^^^^^^^^^^^^

by `@FrankStain <https://github.com/pydoit/doit/issues/207#issuecomment-333367177>`_ (2017-10-01)

I'm professional game developer. Also, i support my own huge game framework written on C++. :)

So, the large scalable build systems are the game building automation tools. It consists of game binary image builders for different platforms, including cross-compilation of source code and source code generation from some DSL schemes. Also it consists of resource generators, where a lot of resource types (dozens of types: textures, 3d objects and scene graphs, sounds, database and state machine raw data) have to pass through dozens of compilation steps. After all, such build system consists of dynamic testing tool, which makes some tests on build target before make it published for Draft usage, QA or Retail customers. And, yep, publishing/QA deployment also implemented as part of build system.

Just imagine you need to read PNG into pixelmap, compress it into ETC2, ATCI, S3-TC5/BC3 and PVR-TC4, after what each of compressed texture should be placed into different resource pack, obfuscated and encrypted. And all is done by different tasks, because i can read textures even from database, zip-file or other pack and may not wish to compress it into some formats.
Each sound should be loaded from PCM, converted into MP3 or OGG and linked with each sound mixer where it used, after what it also have to be placed at proper resource pack, obfuscated and encrypted.
3d location compilation process is about two hundreds tasks on just objects, not files. It's most complex resource pipeline in build system.

`doit` is well designed tool for such purposes, i think.


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
customer facing deliverable. Previously we used makefiles to coordinate builds. `doit`
let us create a system that can be more easily maintained, tested, and extended using
plugins.




DevOps
------


University of Oslo Library, Norway
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by_ `Dan Michael O. Heggø <https://github.com/danmichaelo>`_ (2018-02-26)

.. _by: #https-data-ub-uio-no

We're using `doit` for the publishing workflow at our vocabulary server https://data.ub.uio.no/ .
The server checks multiple remote sources for changes, and when there’s new changes somewhere, the data is fetched,
converted to different formats, published and pushed to Fuseki and Elasticsearch.

One part I love about `doit` is that you can control what is considered a change.
For remote files, I've created a task that checks if some header, like ETag or Last-Modified, has changed.
If it hasn't, I set `uptodate` to True and stop there.

Another part I love is the ability to re-use tasks.
Each vocabulary (like https://github.com/realfagstermer/realfagstermer and https://github.com/scriptotek/humord)
has a different publication workflow, but many tasks are shared.
With `doit`, I've created a collection of tasks and task generators (https://github.com/scriptotek/data_ub_tasks/)
that I use with all the vocabularies.

Finally, it's great that you can mix shell commands and Python tasks so easily.
This cuts development time and makes the move from using Makefiles much easier.
