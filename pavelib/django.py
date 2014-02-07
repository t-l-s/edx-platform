from paver.easy import *
from .utils.process import write_stderr, run_process, run_multi_processes

DEFAULT_PORT = {"lms": 8000, "cms": 8001}


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("port=", "p", "Port")
])
def cms(options):
    """
    Runs cms with the supplied environment and optional port
    """
    setattr(options, 'system', 'cms')
    run_server(options)


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("port=", "p", "Port")
])
def lms(options):
    """
    Runs lms with the supplied environment and optional port
    """
    setattr(options, 'system', 'lms')
    run_server(options)


@task
@cmdopts([
    ("system=", "s", "System to act on"),
    ("env=", "e", "Environment settings"),
    ("port=", "p", "Port")
])
def run_server(options):
    """
    Runs server specified by system using a supplied environment
    """
    system = getattr(options, 'system', 'lms')
    env = getattr(options, 'env', 'dev')
    port = getattr(options, 'port', 0)

    if not port:
        port = DEFAULT_PORT[system]

    run_process(
        'python manage.py {system} runserver --traceback --settings={env} --pythonpath=. {port}'.format(
            system=system, env=env, port=port))


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
])
def resetdb():
    """
    Runs syncdb and then migrate
    """
    env = getattr(options, 'env', 'dev')

    sh('python manage.py lms syncdb --traceback --settings={env}  --pythonpath=. '.format(env=env))
    sh('python manage.py lms migrate --traceback --settings={env}  --pythonpath=. '.format(env=env))


@task
@cmdopts([
    ("system=", "s", "System to act on"),
    ("env=", "e", "Environment settings"),
])
def check_settings():
    """
    Checks settings files
    """
    system = getattr(options, 'system', 'lms')
    env = getattr(options, 'env', 'dev')

    try:
        sh(("echo 'import {system}.envs.{env}' | python manage.py {system} shell --plain --settings={env} --pythonpath=. ".format(system=system, env=env)))
    except:
        write_stderr("Failed to import settings")
        return


@task
@cmdopts([
    ("system=", "s", "System to act on"),
    ("env=", "e", "Environment settings"),
])
def run_celery():
    """
    Runs celery for the specified system
    """
    system = getattr(options, 'system', 'lms')
    env = getattr(options, 'env', 'dev_with_worker')

    run_process('python manage.py {system} celery worker --loglevel=INFO --settings={env} --pythonpath=. '.format(
        system=system, env=env))


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("worker_env=", "w", "Celery Worker Environment settings"),
])
def run_all_servers():
    """
    Runs cms, lms and celery workers
    """
    env = getattr(options, 'env', 'dev')
    worker_env = getattr(options, 'env', 'dev_with_worker')

    run_multi_processes(
        ['python manage.py lms runserver --traceback --settings={env}  --pythonpath=. {port}'.format(env=env, port=DEFAULT_PORT['lms']),
         'python manage.py cms runserver --traceback --settings={env}  --pythonpath=. {port}'.format(env=env, port=DEFAULT_PORT['cms']),
         'python manage.py lms celery worker --loglevel=INFO --settings={env} --pythonpath=. '.format(env=worker_env),
         'python manage.py cms celery worker --loglevel=INFO --settings={env} --pythonpath=. '.format(env=worker_env)
         ])


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("src=", "s", "Source location"),
    ("dest=", "d", "Destination location"),
])
def clone_course():
    """
    Clone existing MongoDB based course
    """
    env = getattr(options, 'env', 'dev')
    src = getattr(options, 'src', '')
    dest = getattr(options, 'dest', '')

    if not src or not dest:
        print("You must provide a source and destination")
        exit()

    sh('python manage.py cms clone --traceback --settings={env} --pythonpath=. {src} {dest}'.format(
        env=env, src=src, dest=dest))


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("location=", "l", "Location to delete"),
    ("commit", "c", "Commit"),
])
def delete_course():
    """
    Delete existing MongoDB based course
    """
    env = getattr(options, 'env', 'dev')
    location = getattr(options, 'location', '')
    commit = getattr(options, 'commit', False)

    if not location:
        print("You must provide a location")
        exit()

    commit_arg = 'commit' if commit else ''

    sh('python manage.py cms delete_course --traceback --settings={env} --pythonpath=. {location} {commit}'.format(
        env=env, location=location, commit=commit_arg)
       )


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("data_dir=", "d", "Data directory"),
    ("course_dir=", "c", "Course directory"),
])
def import_course():
    """
    Import course data from a directory
    """
    env = getattr(options, 'env', 'dev')
    data_dir = getattr(options, 'data_dir', '')
    course_dir = getattr(options, 'course_dir', '')

    if not data_dir:
        print("You must provide a directory")
        exit()

    sh('python manage.py cms import --traceback --settings={env} --pythonpath=. {data_dir} {course_dir}'.format(
        env=env, data_dir=data_dir, course_dir=course_dir)
       )


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("data_dir=", "d", "Data directory"),
    ("course_dir=", "c", "Course directory"),
])
def xlint_course():
    """
    xlint course data in a directory
    """
    env = getattr(options, 'env', 'dev')
    data_dir = getattr(options, 'data_dir', '')
    course_dir = getattr(options, 'course_dir', '')

    if not data_dir:
        print("You must provide a directory")
        exit()

    sh('python manage.py cms xlint --traceback --settings={env} --pythonpath=. {data_dir} {course_dir}'.format(
        env=env, data_dir=data_dir, course_dir=course_dir)
       )


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("course_id=", "c", "Course to export"),
    ("output=", "o", "Output path"),
])
def export_course():
    """
    Export course data to a tar.gz file
    """
    env = getattr(options, 'env', 'dev')
    course_id = getattr(options, 'course_id', '')
    output = getattr(options, 'output', '')

    if not course_id or not output:
        print("You must provide a course id and output path")
        exit()

    sh('python manage.py cms export --traceback --settings={env} --pythonpath=. {course_id} {output}'.format(
        env=env, course_id=course_id, output=output)
       )


@task
@cmdopts([
    ("env=", "e", "Environment settings"),
    ("user=", "u", "User to set staff bit"),
])
def set_staff():
    """
    Export course data to a tar.gz file
    """
    env = getattr(options, 'env', 'dev')
    user = getattr(options, 'user', '')

    if not user:
        print("You must provide a user id")
        exit()

    sh('python manage.py cms set_staff --traceback --settings={env} --pythonpath=. {user}'.format(env=env, user=user))
