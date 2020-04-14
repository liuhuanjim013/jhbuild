# jhbuild - a tool to ease building collections of source packages
# Copyright (C) 2019-2020 Mujin
#
#   node.py: node module type definitions, internally uses yarn
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

from jhbuild.modtypes import Package, DownloadableModule, register_module_type


class NodeModule(Package, DownloadableModule):
    """
    """
    PHASE_CHECKOUT = DownloadableModule.PHASE_CHECKOUT
    PHASE_FORCE_CHECKOUT = DownloadableModule.PHASE_FORCE_CHECKOUT
    PHASE_INSTALL_DEPENDENCIES = 'install_dependencies'
    PHASE_INSTALL = 'install'
    PHASE_BUILD = 'build'

    def __init__(self, name, branch=None, nodescript='build'):
        super(NodeModule, self).__init__(name, branch=branch)
        self.name = name
        self.supports_install_destdir = True
        self.nodescript = nodescript

    def do_install_dependencies(self, buildscript):
        """Install dependcies list in package.json

        both dependencies and dev dependencies will be installed under builddir/package_name/node_modules
        """
        buildscript.set_action(_('Installing dependencies'), self)
        srcdir = self.get_srcdir(buildscript)
        builddir = self.get_builddir(buildscript)
        # buildscript.execute('npm install --prefix {}'.format(builddir), cwd=srcdir)
        buildscript.execute('npm run jhbuild-dep', cwd=srcdir, extra_env={
            'BUILDDIR': builddir,
        })
        buildscript.execute('npm install', cwd=builddir)

    do_install_dependencies.depends = [PHASE_CHECKOUT]
    do_install_dependencies.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_build(self, buildscript):
        """Run build command specified in package.json
        """
        buildscript.set_action(_('Building'), self)
        prefix = os.path.expanduser(buildscript.config.prefix)
        destdir = self.prepare_installroot(buildscript)
        builddir = self.get_builddir(buildscript)
        buildscript.execute('npm run %s' % self.nodescript, cwd=builddir, extra_env={
            'NODE_ENV': 'production',
            'PREFIX': prefix,
            'DESTDIR': destdir,
        })

    do_build.depends = [PHASE_INSTALL_DEPENDENCIES]
    do_build.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_install(self, buildscript):
        """ install the output files to installdir
        """
        buildscript.set_action(_('Installing'), self)

        destdir = self.prepare_installroot(buildscript)
        prefix_without_drive = os.path.splitdrive(buildscript.config.prefix)[1]
        stripped_prefix = prefix_without_drive[1:]
        destdir_prefix = os.path.join(destdir, stripped_prefix)

        builddir = self.get_builddir(buildscript)
        buildscript.execute('npm run jhbuild-install', cwd=builddir, extra_env={
            'INSTALLDIR': destdir_prefix,
        })

        self.process_install(buildscript, self.get_revision())

    do_install.depends = [PHASE_BUILD]
    do_install.error_phases = [PHASE_FORCE_CHECKOUT]

    def get_srcdir(self, buildscript):
        """ source file folder
        """
        return self.branch.srcdir

    def get_builddir(self, buildscript):
        return os.path.join(buildscript.config.buildroot, self.name)

    def xml_tag_and_attrs(self):
        return 'node', [
            ('id', 'name', None),
            ('nodescript', 'nodescript', None),
        ]

def parse_node(node, config, uri, repositories, default_repo):
    instance = NodeModule.parse_from_xml(node, config, uri, repositories, default_repo)
    instance.dependencies += ['node'] # add node to the dep
    if node.hasAttribute('nodescript'):
        instance.nodescript = node.getAttribute('nodescript')
    return instance

register_module_type('node', parse_node)
