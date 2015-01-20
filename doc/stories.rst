

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
`Automating an analysis pipeline using doit <http://www.software-carpentry.org/v5/intermediate/doit/>`_.




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



Content Generation
------------------


Nikola
^^^^^^

by `the Nikola team <https://getnikola.com/>`_

`Nikola <https://getnikola.com/>`_ is a Static Site and Blog Generator.  doit
is used to process all the tasks required for building the website (HTML files,
indexes, RSS, copying files…).  Use of doit makes Nikola unique: unlike other
static site generators, Nikola regenerates only the files that were changed
since last build (and not all files in the site!).  ``nikola build``, the
centerpiece of Nikola, is basically the usual ``doit run`` command.

doit is what makes Nikola extremely fast, even for large sites.  Only a handful
of files actually *change* on a rebuild.  Using the dependency architecture of
doit (for files and configuration), we are able to rebuild only what is needed.

Nikola is an `open-source <https://github.com/getnikola/nikola>`_ project with
many users and contributors.
