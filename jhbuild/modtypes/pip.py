# jhbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
#
#   pip.py: Python pip module type definitions.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__metaclass__ = type

import os
import tempfile
import shutil

from jhbuild.errors import SkipToEnd
from jhbuild.modtypes import Package, register_module_type

__all__ = [ 'PipModule' ]

class PipModule(Package):
    """Base type for modules that are distributed with python pip"""
    type = 'pip'

    PHASE_INSTALL = 'install'

    def __init__(self, name, branch=None, supports_non_srcdir_builds=True):
        Package.__init__(self, name, branch=branch)
        self.supports_install_destdir = True
        self.python = [os.environ.get('PYTHON', 'python')]

    def do_install(self, buildscript):
        if self.check_build_policy(buildscript) == self.PHASE_DONE:
            raise SkipToEnd()

        buildscript.set_action(_('Installing'), self)
        destdir = self.prepare_installroot(buildscript)
        tempdir = tempfile.mkdtemp()

        for python in self.python:
            cmd = [python, '-m', 'pip']
            cmd.extend(['install',
                    '--verbose',
                    '--no-dependencies',
                    '--ignore-installed',
                    '--prefix', buildscript.config.prefix,
                    '--build', os.path.join(tempdir, 'build'),
                    '--src', os.path.join(tempdir, 'src'),
                    '--root', destdir] + self.branch.version.split())
            buildscript.execute(cmd, cwd=tempdir, extra_env=self.extra_env)

        self.process_install(buildscript, self.branch.version)

        shutil.rmtree(tempdir)

    def xml_tag_and_attrs(self):
        return 'pip', [
            ('id', 'name', None),
            ('python', 'python', None),
            ('supports-stripping-debug-symbols', 'supports_stripping_debug_symbols', None),
        ]

def parse_pip(node, config, uri, repositories, default_repo):
    instance = PipModule.parse_from_xml(node, config, uri, repositories, default_repo)
    instance.dependencies += ['pip']

    # allow to specify python executable separated by space
    if node.hasAttribute('python'):
        instance.python = node.getAttribute('python').split()

    if node.hasAttribute('supports-stripping-debug-symbols'):
        instance.supports_stripping_debug_symbols = (node.getAttribute('supports-stripping-debug-symbols') != 'no')

    return instance

register_module_type('pip', parse_pip)

