*******************************************
Paver
*******************************************


Paver provides a standardised way of managing development and operational tasks in edX.

To run individual commands, use the following syntax:

paver <command_name> --option=<option value>


Paver Commands
*******************************************

Paver commands are grouped as follows:

- Prereqs_ Install all of the prerequisite environments for python, node and ruby
- Docs_ Docs is used to build and then optionally display the edX docs relating to development, authoring and data management
- Assets_ Assets will compile sass (css), coffeescript (javascript) and xmodule assets. Optionally it can call django’s collectstatic method
- `Run Servers`_ Run servers
- `Developer Stack`_ Management of developer vagrant environment
- Workspace_ Migration utilities


.. _Prereqs:

Prereqs
=============

Install all of the prerequisite environments for python, node and ruby

   **install_prereqs** : installs ruby, node and python

::

   paver install_prereqs

..

Runs following commands:

   **install_ruby_prereqs** : Installs ruby prereqs. Reguires bundler

::

   paver install_ruby_prereqs

..

   **install_node_prereqs**: Installs Node prereqs. Requires npm

::

   paver install_node_prereqs

..

   **install_python_prereqs**: Installs Python prereqs. Requires pip

::

   paver install_python_prereqs

..


.. _Docs:

Docs
=============

Docs is used to build and then optionally display the edX docs relating to development, authoring and data management

   **build_docs**:  Invoke sphinx 'make build' to generate docs.

    **--type=** <dev, author, data> Type of docs to compile

    **--verbose** Display verbose output

::

   paver build_docs --type=dev --verbose

..

   **show_docs**: Show docs in browser

    *--type=* <dev, author, data> Type of docs to compile

::

   paver show_docs --type=dev

..

   **doc**:  Invoke sphinx 'make build' to generate docs and then show in browser

    *--type=* <dev, author, data> Type of docs to compile

    *--verbose* Display verbose output

::

   paver doc --type=dev --verbose

..


.. _Assets:

Assets
=============

Assets will compile sass (css), coffeescript (javascript) and xmodule assets. Optionally it can call django's
collectstatic method


   **compile_coffeescript**: Compiles Coffeescript files

    *--system=*   System to act on e.g. lms, cms

    *--env=*      Environment settings e.g. aws, dev

    *--watch*     Run with watch

    *--debug*     Run with debug

    *--clobber*   Remove compiled Coffeescript files

::

   paver compile_coffeescript --system=lms --env=dev --watch --debug

..

   **compile_sass**: Compiles Sass files

    *--system=* System to act on e.g. lms, cms

    *--env=* Environment settings e.g. aws, dev

    *--watch* Run with watch

    *--debug* Run with debug

::

   paver compile_sass --system=lms --env=dev --watch --debug

..

   **compile_xmodule**: Compiles Xmodule

    *--system=* System to act on e.g. lms, cms

    *--env=* Environment settings e.g. aws, dev

    *--watch* Run with watch

    *--debug* Run with debug

::

   paver compile_xmodule --system=lms --env=dev --watch --debug

..


   **compile_assets**: Compiles Coffeescript, Sass, Xmodule and optionally runs collectstatic

    *--system=* System to act on e.g. lms, cms

    *--env=* Environment settings e.g. aws, dev

    *--watch* Run with watch

    *--debug* Run with debug

    *--collectstatic* Runs collectstatic

::

   paver compile_sass --system=lms --env=dev --watch --debug

..

.. _Run Servers:

Run Servers
=============

    **lms**: runs lms

     *--env=* Environment settings e.g. aws, dev

::

   paver lms --env=dev

..


    **cms**: runs cms

     *--env=* Environment settings e.g. aws, dev

::

   paver cms --env=dev

..

    **run_server**: run a specific server

     *--system=* System to act on e.g. lms, cms

     *--env=* Environment settings e.g. aws, dev

::

   paver run_server --system=lms --env=dev

..

    **resetdb**: runs syncdb and then migrate

     *--env=* Environment settings e.g. aws, dev

::

   paver resetdb --env=dev

..


    **check_settings**: checks settings files

     *--env=* Environment settings e.g. aws, dev

::

   paver check_settings --env=dev

..


    **run_all_servers**: runs lms, cms and celery workers

     *--env=* Environment settings e.g. aws, dev

     *--worker_env=* Environment settings for celery workers


::

   paver run_all_servers --env=dev --worker_env=celery

..


    **run_celery**: runs celery for specified system

     *--system=* System to act on e.g. lms, cms

     *--env=* Environment settings e.g. aws, dev

::

   paver run_celery --system=lms --env=dev

..

.. _Developer Stack:

Developer Stack
===============

Management of developer vagrant environment




    **devstack_assets**: Update static assets

     *--system=*   System to act on e.g. lms, cms

::

   paver devstack_assets --system=lms

..


    **devstack_start**: Start the server specified

     *--system=*   System to act on e.g. lms, cms

::

   paver devstack_start --system=lms

..



    **devstack_install**: Update Python, Ruby, and Node requirements

::

   paver devstack_install

..


    **devstack**: Install prerequisites, compile assets and run the system specified

     *--system=*   System to act on e.g. lms, cms

::

   paver devstack --system=lms

..


.. _Workspace:

Workspace
=========

Migration tool to run arbitrary scripts


    **workspace_migrate**: Run scripts in ws_migrations directory

::

   paver workspace_migrate

..
