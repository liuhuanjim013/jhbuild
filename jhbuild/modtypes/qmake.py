# jhbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
#
#   qmake.py: qmake module type definitions.
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

from jhbuild.errors import BuildStateError, CommandError
from jhbuild.modtypes import \
     Package, DownloadableModule, register_module_type, MakeModule
from jhbuild.commands.sanitycheck import inpath

__all__ = [ 'QMakeModule' ]

class QMakeModule(MakeModule, DownloadableModule):
    """Base type for modules that use QMake build system."""
    type = 'qmake'

    PHASE_CHECKOUT = DownloadableModule.PHASE_CHECKOUT
    PHASE_FORCE_CHECKOUT = DownloadableModule.PHASE_FORCE_CHECKOUT
    PHASE_CONFIGURE = 'configure'
    PHASE_BUILD = 'build'
    PHASE_INSTALL = 'install'

    def __init__(self, name, branch=None, qmakeargs='', makeargs=''):
        MakeModule.__init__(self, name, branch=branch, makeargs=makeargs)
        self.qmakeargs = qmakeargs
        self.supports_non_srcdir_builds = False
        self.supports_install_destdir = True

    def get_srcdir(self, buildscript):
        return self.branch.srcdir

    def get_builddir(self, buildscript):
        return self.get_srcdir(buildscript)

    def do_configure(self, buildscript):
        buildscript.set_action(_('Configuring'), self)
        builddir = self.get_builddir(buildscript)
        destdir = self.prepare_installroot(buildscript)

        if not inpath('qmake', os.environ['PATH'].split(os.pathsep)):
            raise CommandError(_('%s not found') % 'qmake')

        # qmake leaves Makefiles that cannot be updated
        if hasattr(self.branch, 'delete_unknown_files'):
            self.branch.delete_unknown_files(buildscript)

        qmakeargs = self.eval_args(self.qmakeargs)
        qmakeargs = qmakeargs.replace('${destdir}', destdir)
        cmd = 'qmake %s' % qmakeargs
        buildscript.execute(cmd, cwd = builddir, extra_env = self.extra_env)
    do_configure.depends = [PHASE_CHECKOUT]
    do_configure.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_clean(self, buildscript):
        buildscript.set_action(_('Cleaning'), self)
        if hasattr(self.branch, 'delete_unknown_files'):
            self.branch.delete_unknown_files(buildscript)
        else:
            self.make(buildscript, 'clean')
    do_clean.depends = [PHASE_CONFIGURE]
    do_clean.error_phases = [PHASE_FORCE_CHECKOUT, PHASE_CONFIGURE]

    def do_build(self, buildscript):
        buildscript.set_action(_('Building'), self)
        self.make(buildscript)
    do_build.depends = [PHASE_CONFIGURE]
    do_build.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_install(self, buildscript):
        buildscript.set_action(_('Installing'), self)
        # self.make(buildscript, 'install')
        # qt5 version of qmake has only one way of controlling the install prefix for the modules, and that is through INSTALL_ROOT
        destdir = self.prepare_installroot(buildscript)
        makeargs = self.get_makeargs(self, buildscript) + ' INSTALL_ROOT="' + destdir + '"'
        self.make(buildscript, 'install', makeargs=makeargs)

        self.process_install(buildscript, self.get_revision())
    do_install.depends = [PHASE_BUILD]

    def xml_tag_and_attrs(self):
        return 'qmake', [('id', 'name', None)]


def parse_qmake(node, config, uri, repositories, default_repo):
    instance = QMakeModule.parse_from_xml(node, config, uri, repositories, default_repo)
    instance.dependencies += ['qmake', instance.get_makecmd(config)]
    if node.hasAttribute('qmakeargs'):
        instance.qmakeargs = node.getAttribute('qmakeargs')
    if node.hasAttribute('makeargs'):
        instance.makeargs = node.getAttribute('makeargs')
    return instance

register_module_type('qmake', parse_qmake)

