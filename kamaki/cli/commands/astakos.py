# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from kamaki.cli import command
from kamaki.clients.astakos import AstakosClient
from kamaki.cli.commands import (
    _command_init, errors, _optional_json, addLogSettings)
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import CLIBaseUrlError
from kamaki.cli.utils import print_dict

user_cmds = CommandTree('user', 'Astakos API commands')
_commands = [user_cmds]


class _user_init(_command_init):

    @errors.generic.all
    @errors.user.load
    @addLogSettings
    def _run(self):
        if getattr(self, 'cloud', False):
            base_url = self._custom_url('astakos')
            if base_url:
                token = self._custom_token('astakos')\
                    or self.config.get_remote(self.cloud, 'token')
                self.client = AstakosClient(base_url=base_url, token=token)
                return
        else:
            self.cloud = 'default'
        if getattr(self, 'auth_base', False):
            self.client = self.auth_base
            return
        raise CLIBaseUrlError(service='astakos')

    def main(self):
        self._run()


@command(user_cmds)
class user_authenticate(_user_init, _optional_json):
    """Authenticate a user
    Get user information (e.g. unique account name) from token
    Token should be set in settings:
    *  check if a token is set    /config get remote.default.token
    *  permanently set a token    /config set remote.default.token <token>
    Token can also be provided as a parameter
    (In case of another named cloud remote, use its name instead of default)
    """

    @staticmethod
    def _print_access(r):
        print_dict(r['access'])

    @errors.generic.all
    @errors.user.authenticate
    def _run(self, custom_token=None):
        super(self.__class__, self)._run()
        r = self.client.authenticate(custom_token)
        self._print(r, self._print_access)

    def main(self, custom_token=None):
        self._run(custom_token)
