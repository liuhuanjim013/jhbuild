import os
import sys

# only allow loading python packages from the correct versioned locations
dirnames = [
    'python%d.%d' % (sys.version_info[0], sys.version_info[1]),
    'python%d' % (sys.version_info[0]),
    'python',
]
libpaths = set()

pathstoremove = set()
for path in list(sys.path):
    for dirname in path.split(os.path.sep):
        if dirname.startswith('python') and dirname not in dirnames:
            pathstoremove.add(path)
            libpaths.add(path.split(dirname)[0])
            break

# remove paths that are for different version of python
for path in pathstoremove:
    while path in sys.path:
        sys.path.remove(path)

# make sure site-packages and dist-packages are there
for libpath in libpaths:
    for subdir in ['dist-packages', 'site-packages']:
        path = os.path.join(libpath, subdir)
        if path not in sys.path:
            sys.path.append(path)

# the deal with this file is that the *.pth files is only executed
# when it is added as site dir
# however, python only import the first sitecustomize.py it sees
# so we need to add all site dirs here

import site
paths = list(sys.path)
for path in paths:
    dirname = path.rsplit(os.path.sep, 1)[-1]
    if dirname in ['dist-packages', 'site-packages']:
        site.addsitedir(path)

# change system wide default encoding from ascii to utf-8
if sys.version_info[0] == 2:
    sys.setdefaultencoding('utf-8')

