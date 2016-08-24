# setup.py
# use py2exe to convert Python script and dependencies to a closed standalone executable file(s)

# 2 directories will be created when you run your setup script, build and dist:
# - The build directory is used as working space while your application is being packaged. Can be deleted after setup script has finished running.
# - The files in the dist directory are the ones needed to run your application.

# USAGE :: python setup.py py2exe -c -d nifti2xnat.exe

from distutils.core import setup
import py2exe
setup(console=['nifti2xnat.py'])
