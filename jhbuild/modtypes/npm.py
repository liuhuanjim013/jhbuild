# jhbuild - a tool to ease building collections of source packages
# Copyright (C) 2019-2024 Mujin
#
#   npm.py: npm module type definitions.
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
__all__ = ["NPMModule"]

import os
import shutil
from jhbuild.errors import BuildStateError, CommandError
from jhbuild.modtypes import \
    Package, DownloadableModule, register_module_type
from jhbuild.modtypes.autotools import collect_args

import logging

class NPMModule(Package, DownloadableModule):
    """
    """
    PHASE_CHECKOUT = DownloadableModule.PHASE_CHECKOUT
    PHASE_FORCE_CHECKOUT = DownloadableModule.PHASE_FORCE_CHECKOUT
    PHASE_INSTALL_DEPENDENCIES = 'install_dependencies'
    PHASE_INSTALL = 'install'
    PHASE_BUILD = 'build'

    skip_install_phase = False

    # package name
    name = ''

    # e.g. install user-defined-dir
    # e.g. run-script install
    npmargs = ''

    # a package is usually a folder containing a program described by package.json file
    # https://docs.npmjs.com/about-packages-and-modules
    # locate the package.json file
    packagedir = ''

    # npm command 
    npmcmd = None
    extraenv = None

    def __init__(self, name, branch=None, npmargs=''):
        self.name = name
        self.npmargs = npmargs
        super(NPMModule, self).__init__(name, branch=branch)

    def do_install_dependencies(self, buildscript):
        """ Install dependcies list in packages.json
        
        dependencies will be installed under builddir/package_name/node_moduels
        """
        buildscript.set_action(_('Installing Package Dependencies'), self)

        source = os.path.join(self.get_srcdir(buildscript), self.packagedir, 'package.json')
        dest = os.path.join(self.get_builddir(buildscript), 'package.json')
        if not os.path.exists(self.get_builddir(buildscript)):
            os.makedirs(self.get_builddir(buildscript))
        shutil.copyfile(source, dest)
        self.npm(buildscript, 'install', npmargs='--prefix %s' % self.get_builddir(buildscript))

    def do_build(self, buildscript):
        """ run npm run-script build
        """
        packagedir = os.path.join(self.get_srcdir(buildscript), self.packagedir)
        self.npm(buildscript, 'run-script build %s' % packagedir, npmargs='--prefix %s' % self.get_builddir(buildscript))

    do_build.depends = [PHASE_INSTALL_DEPENDENCIES]
    do_build.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_install(self, buildscript):
        """ install the output files to installdir
        """
        buildscript.set_action(_('Installing'), self)
        destdir = self.prepare_installroot(buildscript)
        # TODO copy compiled output file to destdir
        self.process_install(buildscript, self.get_revision())

    do_install.depends = [PHASE_BUILD]
    do_install.error_phases = [PHASE_FORCE_CHECKOUT]

    def get_srcdir(self, buildscript):
        """ source file folder
        """
        return self.branch.srcdir

    def get_builddir(self, buildscript):
        return os.path.join(buildscript.config.buildroot, self.name)
    

    def get_npmcmd(self, config):
        if self.npmcmd:
            return self.npmcmd
        return 'npm'

    def get_npmargs(self, buildscript):
        npmargs = ' %s %s' % (self.npmargs, self.config.module_npmargs.get(self.name, self.config.npmargs))
        return self.eval_args(npmargs).strip()

    def npm(self, buildscript, target='', npmargs=None, env=None):
        npmcmd = os.environ.get('NPM', self.get_npmcmd(buildscript.config)) # TODO

        if npmargs is None:
            npmargs = self.get_npmargs(buildscript)

        extra_env = (self.extraenv or {}).copy()
        for k in (env or {}):
            extra_env[k] = env[k]

        cmd = '{npm} {npmargs} {target}'.format(npm=npmcmd,
                                                npmargs=npmargs,
                                                target=target)
        buildscript.execute(cmd, cwd=self.get_builddir(buildscript), extra_env=extra_env)

    def xml_tag_and_attrs(self):
        return 'npm', [('id', 'name', None),]

def parse_npm(node, config, uri, repositories, default_repo):
    instance = NPMModule.parse_from_xml(node, config, uri, repositories, default_repo)
    instance.dependencies += ['npm']

    instance.npmargs = collect_args(instance, node, 'npmargs')

    instance.packagedir = os.path.join(instance.get_srcdir(), collect_args(instance, node, 'packagedir'))
    
    if node.hasAttribute('skip-install'):
        skip_install = node.getAttribute('skip-install')
        if skip_install.lower() in ('true', 'yes'):
            instance.skip_install_phase = True
        else:
            instance.skip_install_phase = False

    return instance

register_module_type('npm', parse_npm)
