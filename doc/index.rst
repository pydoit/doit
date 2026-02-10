.. meta::
   :description: doit — Python task runner with DAG execution, dependency tracking, and incremental builds
   :keywords: python, pydoit, doit, task runner, build tool, automation, DAG, incremental build, dependency tracking
   :og\:title: pydoit — Python Task Runner & Automation Tool
   :og\:description: Define tasks in Python. Run only what changed. A task management & automation tool with DAG execution, dependency tracking, and incremental builds.
   :og\:type: website
   :og\:url: https://pydoit.org
   :og\:image: https://pydoit.org/_static/doit-logo.png
   :og\:site_name: pydoit
   :twitter\:card: summary
   :twitter\:title: pydoit — Python Task Runner & Automation Tool
   :twitter\:description: Define tasks in Python. Run only what changed. DAG execution, dependency tracking, and incremental builds.
   :twitter\:image: https://pydoit.org/_static/doit-logo.png

.. title:: pydoit — Python Task Runner & Automation Tool


.. raw:: html

   <div class="landing-hero">
     <img src="_static/doit-logo.png" alt="doit logo" class="hero-logo">
     <h1><strong>Define tasks in Python.</strong><br>Run only what changed.</h1>
     <p class="hero-subtitle">
       A task management &amp; automation tool like <code class="hero-code">make</code>,
       but in pure Python.<br>
       Tracks file dependencies, caches results, and skips tasks that are already up-to-date.
     </p>
     <div class="hero-actions">
       <pre class="install-cmd"><code>pip install doit</code></pre>
       <a class="hero-btn" href="contents.html">Documentation</a>
       <a class="github-stars" href="https://github.com/pydoit/doit"><img src="https://img.shields.io/github/stars/pydoit/doit?style=social" alt="GitHub stars"></a>
     </div>
     <p class="hero-compare">
       Often compared to <em>make</em>, <em>just</em>, <em>invoke</em>,
       and <em>snakemake</em> — but with DAG execution and incremental
       builds built in.
     </p>
   </div>


Quick Example
-------------

.. raw:: html

   <p class="section-lead">Create a <code>dodo.py</code> — tasks are plain Python dicts.</p>

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item::

      .. code-block:: python
         :caption: dodo.py

         def task_hello():
             """create a greeting file"""
             return {
                 'actions': ['echo "Hello from doit" > hello.txt'],
                 'targets': ['hello.txt'],
                 'clean': True,
             }

         def task_shout():
             """convert greeting to uppercase"""
             return {
                 'actions': ['tr a-z A-Z < hello.txt > shout.txt'],
                 'file_dep': ['hello.txt'],
                 'targets': ['shout.txt'],
                 'clean': True,
             }

   .. grid-item::

      .. code-block:: console
         :caption: Terminal

         $ pip install doit
         $ doit
         .  hello
         .  shout
         $ doit            # nothing to do — already up-to-date
         -- hello
         -- shout
         $ doit clean      # remove generated files
         $ doit            # runs again
         .  hello
         .  shout


----


Python-Native Task Runner
-------------------------

.. raw:: html

   <p class="section-lead">No DSL, no YAML — tasks are plain Python dicts and functions.</p>

   <div class="feature-section">
     <dl class="feature-list">
       <dt>Pure Python</dt>
       <dd>Tasks are Python dicts. Use any library, generate tasks programmatically, debug with <em>pdb</em>.</dd>
       <dt>Shell or Python actions</dt>
       <dd>Run shell commands, call Python functions, or mix both in a single task.</dd>
       <dt>Self-documenting</dt>
       <dd><code>doit list</code> shows all tasks with docstrings. <code>doit help &lt;task&gt;</code> for details.</dd>
     </dl>
     <aside class="use-case">
       <strong>In practice:</strong> A <a href="/stories.html#game-development">game developer</a> uses <code>doit</code> to automate code generation, cross-compilation, and resource generation — simplifying cumbersome command line calls and skipping tasks already done.
     </aside>
   </div>


Incremental Builds & Pipelines
------------------------------

.. raw:: html

   <p class="section-lead">DAG execution with dependency tracking — run only what changed.</p>

   <div class="feature-section">
     <dl class="feature-list">
       <dt>Incremental builds</dt>
       <dd>Tracks file dependencies and targets (MD5 or timestamp). Skips tasks that are already up-to-date.</dd>
       <dt>Flexible up-to-date checks</dt>
       <dd>Not limited to file timestamps. Computed dependencies (<code>calc_dep</code>), custom checkers, and result-based checks.</dd>
       <dt>Pipelines</dt>
       <dd>Pass results between tasks without intermediate files. Dynamic task creation via <code>yield</code> for complex workflows.</dd>
     </dl>
     <aside class="use-case">
       <strong>In practice:</strong> A <a href="/stories.html#computational-metagenomics-lab-university-of-trento-italy">bioinformatics lab</a> uses <code>doit</code> to create reproducible computational pipelines, managing complex dependent workflows and skipping steps already completed.
     </aside>
   </div>


Advanced Features
-----------------

.. raw:: html

   <div class="feature-section">
     <dl class="feature-list">
       <dt>Extensible</dt>
       <dd><strong>Plugin architecture</strong> — custom commands, storage backends, task loaders, and output reporters.
           <strong>Framework API</strong> — build your own tools on top of <em>doit</em>.</dd>
       <dt>Batteries included</dt>
       <dd><strong>Parallel execution</strong> (threaded or multi-process) · <strong>Shell tab-completion</strong> (bash and zsh) · <strong>DAG visualisation</strong> (graphviz).</dd>
     </dl>
     <aside class="use-case">
       <strong>In practice:</strong> <a href="https://getnikola.com/">Nikola</a>, a static site generator, is built on top of <code>doit</code> — using it for the CLI, parallel task execution, and incremental rebuilds.
     </aside>
   </div>


----


.. raw:: html

   <h2 class="testimonials-heading">What people are saying</h2>

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *Congratulations!* **Your tool follows the KISS principle very closely.**
      *I always wondered why build tools had to be that complicated.*

      .. raw:: html

         <p class="testimonial-author">— Elena</p>

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *Let me start by saying I'm really lovin doit, at first the interface
      seemed verbose but quickly changed my mind when*
      **I started using it and realized the flexibility.**

      .. raw:: html

         <p class="testimonial-author">— Michael Gliwinski</p>

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *I love all the traditional unix power tools, like cron, make, perl...
      I also like new comprehensive configuration management tools like
      CFEngine and Puppet. But*
      **I find doit to be so versatile and so productive.**

      .. raw:: html

         <p class="testimonial-author">— Charlie Guo</p>

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *I needed a sort of make tool to glue things together and after trying
      out all kinds,* **doit ... has actually turned out to be beautiful.**
      *Its easy to add and manage tasks, even complex ones.*

      .. raw:: html

         <p class="testimonial-author">— Matthew</p>


.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *I went back and forth on different Pythonic build tools for awhile...
      I've been using doit more and more, and I'm continually impressed.*
      **It works amazingly well for automating tricky/exotic build processes.**

      .. raw:: html

         <p class="testimonial-author">— SkOink</p>

   .. grid-item-card::
      :shadow: none
      :class-card: testimonial-card

      *I grew frustrated with Make and Ant and started porting my build files
      to every build tool I found. Each time I ran into stumbling blocks.*
      **Then I discovered this little gem of simplicity: doit.**

      .. raw:: html

         <p class="testimonial-author">— lelele</p>

----


.. raw:: html

   <div class="status-section">
     <p>
       <code>doit</code> is a mature project actively maintained since
       <a href="http://schettino72.wordpress.com/2008/04/14/doit-a-build-tool-tale">2008</a>.
       Python 3.10+. 99% unit-test code coverage.
       Contributions welcome — development is driven by real-world use cases.
     </p>
     <p>
       <a href="https://opensource.org/licenses/mit-license.php">MIT License</a> ·
       <a href="https://pypi.python.org/pypi/doit">PyPI</a> ·
       <a href="https://github.com/pydoit/doit">GitHub</a> ·
       <a href="support.html">Support</a> ·
       <a href="contents.html">Documentation</a>
     </p>
   </div>


.. toctree::
   :hidden:

   contents

.. toctree::
   :hidden:
   :caption: Getting Started

   usecases
   tutorial-1

.. toctree::
   :hidden:
   :caption: Reference

   install
   tasks
   dependencies
   task-creation
   cmd-run
   cmd-other
   configuration
   task-args
   globals
   uptodate
   tools
   extending

.. toctree::
   :hidden:
   :caption: Project

   support
   changes
   stories
   faq
   related
