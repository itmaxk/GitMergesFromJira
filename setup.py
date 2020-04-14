from cx_Freeze import setup, Executable

executables = [Executable('main.py')]

setup(name='Parser GitLab MR status',
      version='0.0.1',
      description='Parser GitLab MRs statuses from Jira releases',
      executables=executables)