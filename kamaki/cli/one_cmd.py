# Copyright 2012-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.command

from kamaki.cli import (
    get_command_group, set_command_params, print_subcommands_help, exec_cmd,
    update_parser_help, _groups_help, _load_spec_module,
    init_cached_authenticator, kloger)
from kamaki.cli.errors import CLIUnknownCommand


def _get_cmd_tree_from_spec(spec, cmd_tree_list):
    for tree in cmd_tree_list:
        if tree.name == spec:
            return tree
    raise CLIUnknownCommand('Unknown command: %s' % spec)


def _get_best_match_from_cmd_tree(cmd_tree, unparsed):
    matched = [term for term in unparsed if not term.startswith('-')]
    while matched:
        try:
            return cmd_tree.get_command('_'.join(matched))
        except KeyError:
            matched = matched[:-1]
    return None


def run(cloud, parser):
    group = get_command_group(list(parser.unparsed), parser.arguments)
    if not group:
        #parser.parser.print_help()
        parser.print_help()
        _groups_help(parser.arguments)
        exit(0)

    nonargs = [term for term in parser.unparsed if not term.startswith('-')]
    set_command_params(nonargs)

    global _best_match
    _best_match = []

    _cnf = parser.arguments['config']
    group_spec = _cnf.get('global', '%s_cli' % group)
    spec_module = _load_spec_module(group_spec, parser.arguments, 'namespaces')
    if spec_module is None:
        raise CLIUnknownCommand(
            'Could not find specs for %s commands' % group,
            details=[
                'Make sure %s is a valid command group' % group,
                'Refer to kamaki documentation for setting custom command',
                'groups or overide existing ones'])
    cmd_tree = _get_cmd_tree_from_spec(group, spec_module.namespaces)

    if _best_match:
        cmd = cmd_tree.get_command('_'.join(_best_match))
    else:
        cmd = _get_best_match_from_cmd_tree(cmd_tree, parser.unparsed)
        _best_match = cmd.path.split('_')
    if cmd is None:
        kloger.info('Unexpected error: failed to load command (-d for more)')
        exit(1)

    update_parser_help(parser, cmd)

    _help = parser.arguments['help'].value
    if _help or not cmd.is_command:
        if cmd.cmd_class:
            parser.required = getattr(cmd.cmd_class, 'required', None)
        parser.print_help()
        if getattr(cmd, 'long_help', False):
            print 'Details:\n', cmd.long_help
        print_subcommands_help(cmd)
        exit(0)

    cls = cmd.cmd_class
    auth_base = init_cached_authenticator(_cnf, cloud, kloger) if (
        cloud) else None
    executable = cls(parser.arguments, auth_base, cloud)
    parser.required = getattr(cls, 'required', None)
    parser.update_arguments(executable.arguments)
    for term in _best_match:
        parser.unparsed.remove(term)
    exec_cmd(executable, parser.unparsed, parser.print_help)
