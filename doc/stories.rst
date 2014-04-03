

Success Stories
====================

.. contents::
   :local:

Scientific
------------

Biomechanics Lab / Stanford University, USA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

by `Christopher Dembia <http://chrisdembia.github.io>`_


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
