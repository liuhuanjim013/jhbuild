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

    bundler = ''
    bundlerargs = ''

    npmcmd = None
    npmargs = ''

    extraenv = None

    supports_install_destdir = True

    def __init__(self, name, branch=None, npmargs=''):
        super(NPMModule, self).__init__(name, branch=branch)
        self.name = name
        self.npmargs = npmargs
        self.supports_install_destdir = True

    def do_install_dependencies(self, buildscript):
        """ Install dependcies list in packages.json

        dependencies will be installed under builddir/package_name/node_moduels
        """
        buildscript.set_action(_('Installing Package Dependencies'), self)

        source = os.path.join(self.get_srcdir(buildscript), 'package.json')
        dest = os.path.join(self.get_builddir(buildscript), 'package.json')
        if not os.path.exists(self.get_builddir(buildscript)):
            os.makedirs(self.get_builddir(buildscript))
        shutil.copyfile(source, dest)
        self.npm(buildscript, 'install', npmargs='--prefix %s' % self.get_builddir(buildscript))

    def do_build(self, buildscript):
        """ run bundler to build and pack
        """
        self.prepare_installroot(buildscript)
        args = {
            'prefix': self.get_destdir(buildscript) + buildscript.config.prefix
        }
        self.bundlerargs = self.bundlerargs % args
        getattr(self, self.bundler, self.default_bundler)(buildscript)

    do_build.depends = [PHASE_INSTALL_DEPENDENCIES]
    do_build.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_install(self, buildscript):
        """ install the output files to installdir
        """
        buildscript.set_action(_('Installing'), self)
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

    # bundlers               
    def default_bundler(self, buildscript):
        raise CommandError('unknown bundler')

    def webpack(self, buildscript):
        webpack = os.path.join(self.get_builddir(buildscript), 'node_modules/.bin', 'webpack')
        cmd = '%s %s' % (webpack, self.bundlerargs)
        buildscript.execute(cmd, cwd=self.get_srcdir(buildscript))

    def xml_tag_and_attrs(self):
        return 'npm', [('id', 'name', None),]

def parse_npm(node, config, uri, repositories, default_repo):
    instance = NPMModule.parse_from_xml(node, config, uri, repositories, default_repo)
    instance.dependencies += ['npm']

    instance.npmargs = collect_args(instance, node, 'npmargs')
    instance.bundler = collect_args(instance, node, 'bundler')
    instance.bundlerargs = collect_args(instance, node, 'bundlerargs')

    if node.hasAttribute('skip-install'):
        skip_install = node.getAttribute('skip-install')
        instance.skip_install_phase = bool(skip_install.lower() in ('true', 'yes'))

    return instance

register_module_type('npm', parse_npm)
