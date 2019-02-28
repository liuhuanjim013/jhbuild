# jhbuild - a tool to ease building collections of source packages
# Copyright (C) 2011 Colin Walters <walters@verbum.org>
#
#   sysdeps.py: Install system dependencies
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

from optparse import make_option
import logging
import os.path
import subprocess
import sys

import jhbuild.moduleset
from jhbuild.errors import FatalError
from jhbuild.commands import Command, register_command
from jhbuild.commands.base import cmd_build
from jhbuild.utils.systeminstall import SystemInstall
from jhbuild.modtypes.systemmodule import SystemModule
from jhbuild.versioncontrol.tarball import TarballBranch
from jhbuild.utils import cmds
from jhbuild.utils import fileutils

class cmd_sysdeps(cmd_build):
    doc = N_('Check and install tarball dependencies using system packages')

    name = 'sysdeps'

    def __init__(self):
        Command.__init__(self, [
            make_option('--dump',
                        action='store_true', default=False,
                        help=_('Machine readable list of missing sysdeps')),
            make_option('--dump-all',
                        action='store_true', default=False,
                        help=_('Machine readable list of all sysdeps')),
            make_option('--dump-runtime',
                        action='store_true', default=False,
                        help=_('Machine readable list of runtime sysdeps')),
            make_option('--dump-runtime-packages',
                        action='store_true', default=False,
                        help=_('Machine readable list of runtime packages with version')),
            make_option('--install',
                        action='store_true', default=False,
                        help=_('Install pkg-config modules via system'))])


    def _dump_runtime(self, module_list):
        results = []
        for module in module_list:
            if isinstance(module, SystemModule) and module.runtime:
                if module.pkg_config is not None:
                    results.append('pkgconfig:{0}'.format(module.pkg_config[:-3])) # remove .pc

                if module.systemdependencies is not None:
                    for dep_type, value, altdeps in module.systemdependencies:
                        entry = ''
                        entry += '{0}:{1}'.format(dep_type, value)
                        for dep_type, value, empty in altdeps:
                            entry += ',{0}:{1}'.format(dep_type, value)
                        results.append(entry)
        return results


    def _get_all_versioned_pkgs(self):
        """ get all pkgs from `dpkg -l` command. return a dict
        """
        dpkg_list_output = subprocess.check_output(['dpkg', '-l'])
        packages = dpkg_list_output.splitlines()
        results = {}
        for pkg in packages:
            if not pkg.startswith('ii'):
                continue
            pkg_filtered = filter(None, pkg.split(' '))
            results[pkg_filtered[1]] = pkg_filtered[2]
        return results

    def _get_versioned_pkgs(self, pkg_sysdeps):
        fullfilenames = {}
        # split path
        for x in pkg_sysdeps:
            # example: path:/usr/lib/a.so
            # example: path:/usr/lib/a.so,path:/usr/lib/b.so
            f2 = ''
            f1 = x.split(',')[0].split(':')[1].strip()
            if ',' in x:
                f2 = x.split(',')[1].split(':')[1].strip()
            fullfilenames[f1] = f2

        results = {} # packagename: version

        command = ['dpkg', '-S']
        command.extend(fullfilenames.keys())

        dpkg_stdout, dpkg_stderr = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()

        dpkg_stdout = dpkg_stdout.splitlines()
        dpkg_stderr = dpkg_stderr.splitlines()
        if dpkg_stderr:
            old_path = [x[len('dpkg-query: no path found matching pattern '):].strip() for x in dpkg_stderr]
            dpkg_2nd_time = []
            for p in old_path:
                if fullfilenames.get(p ,''):
                    dpkg_2nd_time.append(fullfilenames[p])
                else:
                    logging.error(_('dpkg-query: no path found matching pattern: %s' % p))

            if dpkg_2nd_time:
                command = ['dpkg', '-S']
                command.extend(dpkg_2nd_time)
                dpkg_2_stdout, dpkg_2_stderr = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()

            dpkg_2_stdout = dpkg_2_stdout.splitlines()
            dpkg_2_stderr = dpkg_2_stderr.splitlines()

        if dpkg_2_stderr:
            logging.error(_('\n'.join(dpkg_2_stderr)))

        all_versioned_pkgs = self._get_all_versioned_pkgs()
        for entry in set(dpkg_stdout + dpkg_2_stdout):
            pkg_name = entry.split(':')[0]
            if pkg_name in all_versioned_pkgs:
                results[pkg_name] = all_versioned_pkgs[pkg_name]

        return results

    def run(self, config, options, args, help=None):

        def fmt_details(pkg_config, req_version, installed_version):
            fmt_list = []
            if pkg_config:
                fmt_list.append(pkg_config)
            if req_version:
                fmt_list.append(_('required=%s') % req_version)
            if installed_version and installed_version != 'unknown':
                fmt_list.append(_('installed=%s') % installed_version)
            # Translators: This is used to separate items of package metadata
            fmt_str = _(', ').join(fmt_list)
            if fmt_str:
                return _('(%s)') % fmt_str
            else:
                return ''

        config.set_from_cmdline_options(options)

        module_set = jhbuild.moduleset.load(config)
        modules = args or config.modules
        module_list = module_set.get_full_module_list(modules, config.skip)

        if options.dump_all:
            for module in module_list:
                if (isinstance(module, SystemModule) or isinstance(module.branch, TarballBranch) and
                                                        module.pkg_config is not None):
                    if module.pkg_config is not None:
                        print 'pkgconfig:{0}'.format(module.pkg_config[:-3]) # remove .pc

                    if module.systemdependencies is not None:
                        for dep_type, value, altdeps in module.systemdependencies:
                            sys.stdout.write('{0}:{1}'.format(dep_type, value))
                            for dep_type, value, empty in altdeps:
                                sys.stdout.write(',{0}:{1}'.format(dep_type, value))
                            sys.stdout.write('\n')
            return

        if options.dump_runtime:
            runtimes = self._dump_runtime(module_list)
            sys.stdout.write('\n'.join(runtimes))
            return

        if options.dump_runtime_packages:
            # dump runtime packages with version
            pkg_sysdeps_dir = os.path.join(module_set.config.prefix, '.jhbuild', 'sysdeps')
            pkg_sysdeps = set()
            for pkg_deps_filename in fileutils.accumulate_dirtree_contents(pkg_sysdeps_dir):
                with open(os.path.join(pkg_sysdeps_dir, pkg_deps_filename), 'r') as f:
                    pkg_sysdeps.update(map(lambda x: x.strip(), f.readlines()))

            # dump all runtime packages
            runtimes = self._dump_runtime(module_list)
            # union runtime and pkg_systems
            pkg_sysdeps.update(runtimes)
            results = self._get_versioned_pkgs(pkg_sysdeps)
            for pkg_name, pkg_version in results.items():
                sys.stdout.write(pkg_name + '=' + pkg_version)
                sys.stdout.write('\n')
            return

        module_state = module_set.get_module_state(module_list)

        have_new_enough = False
        have_too_old = False

        if options.dump:
            for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
                if new_enough:
                    continue

                if installed_version is not None and systemmodule:
                    # it's already installed but it's too old and we
                    # don't know how to build a new one for ourselves
                    have_too_old = True

                # request installation in two cases:
                #   1) we don't know how to build it
                #   2) we don't want to build it ourselves
                #
                # partial_build is on by default so this check will only
                # fail if someone explicitly turned it off
                if systemmodule or config.partial_build:
                    assert (module.pkg_config or module.systemdependencies)

                    if module.pkg_config is not None:
                        print 'pkgconfig:{0}'.format(module.pkg_config[:-3]) # remove .pc

                    if module.systemdependencies is not None:
                        for dep_type, value, altdeps in module.systemdependencies:
                            sys.stdout.write('{0}:{1}'.format(dep_type, value))
                            for dep_type, value, empty in altdeps:
                                sys.stdout.write(',{0}:{1}'.format(dep_type, value))
                            sys.stdout.write('\n')

            if have_too_old:
                return 1

            return

        print _('System installed packages which are new enough:')
        for module,(req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if (installed_version is not None) and new_enough and (config.partial_build or systemmodule):
                have_new_enough = True
                print ('    %s %s' % (module.name,
                                      fmt_details(module.pkg_config,
                                                  req_version,
                                                  installed_version)))
        if not have_new_enough:
            print _('  (none)')

        uninstalled = []

        print _('Required packages:')
        print _('  System installed packages which are too old:')
        for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if (installed_version is not None) and (not new_enough) and systemmodule:
                have_too_old = True
                print ('    %s %s' % (module.name,
                                      fmt_details(module.pkg_config,
                                                  req_version,
                                                  installed_version)))
                if module.pkg_config is not None:
                    uninstalled.append((module.name, 'pkgconfig', module.pkg_config[:-3])) # remove .pc
                elif module.systemdependencies is not None:
                    for dep_type, value in module.systemdependencies:
                        uninstalled.append((module.name, dep_type, value))
        if not have_too_old:
            print _('    (none)')

        print _('  No matching system package installed:')
        for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if installed_version is None and (not new_enough) and systemmodule:
                print ('    %s %s' % (module.name,
                                      fmt_details(module.pkg_config,
                                                  req_version,
                                                  installed_version)))
                if module.pkg_config is not None:
                    uninstalled.append((module.name, 'pkgconfig', module.pkg_config[:-3])) # remove .pc
                elif module.systemdependencies is not None:
                    for dep_type, value, altdeps in module.systemdependencies:
                        uninstalled.append((module.name, dep_type, value))
                        for dep_type, value, empty in altdeps:
                            uninstalled.append((module.name, dep_type, value))

        if len(uninstalled) == 0:
            print _('    (none)')

        have_too_old = False

        if config.partial_build:
            print _('Optional packages: (JHBuild will build the missing packages)')
            print _('  System installed packages which are too old:')
            for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
                if (installed_version is not None) and (not new_enough) and (not systemmodule):
                    have_too_old = True
                    print ('    %s %s' % (module.name,
                                          fmt_details(module.pkg_config,
                                                      req_version,
                                                      installed_version)))
                    if module.pkg_config is not None:
                        uninstalled.append((module.name, 'pkgconfig', module.pkg_config[:-3])) # remove .pc
            if not have_too_old:
                print _('    (none)')

            print _('  No matching system package installed:')
            for module,(req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
                if installed_version is None and (not new_enough) and (not systemmodule):
                    print ('    %s %s' % (module.name,
                                          fmt_details(module.pkg_config,
                                                      req_version,
                                                      installed_version)))
                    if module.pkg_config is not None:
                        uninstalled.append((module.name, 'pkgconfig', module.pkg_config[:-3])) # remove .pc

            if len(uninstalled) == 0:
                print _('    (none)')

        if options.install:
            installer = SystemInstall.find_best()
            if installer is None:
                # FIXME: This should be implemented per Colin's design:
                # https://bugzilla.gnome.org/show_bug.cgi?id=682104#c3
                if cmds.has_command('apt-get'):
                    raise FatalError(_("%(cmd)s is required to install "
                                       "packages on this system. Please "
                                       "install %(cmd)s.")
                                     % {'cmd' : 'apt-file'})

                raise FatalError(_("Don't know how to install packages on this system"))

            if len(uninstalled) == 0:
                logging.info(_("No uninstalled system dependencies to install for modules: %r") % (modules, ))
                return

            logging.info(_("Installing dependencies on system: %s") % \
                           ' '.join(pkg[0] for pkg in uninstalled))
            installer.install(uninstalled)

register_command(cmd_sysdeps)

