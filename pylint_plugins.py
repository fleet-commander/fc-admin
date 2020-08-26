""" Plugin to teach Pylint about FreeIPA API
"""

import textwrap

from astroid import MANAGER
from astroid.builder import AstroidBuilder


def register(linter):
    pass


AstroidBuilder(MANAGER).string_build(
    textwrap.dedent(
        """
    from ipalib import api
    from ipalib import plugable

    api.Backend = plugable.APINameSpace(api, None)
    api.Command = plugable.APINameSpace(api, None)
    """
    )
)
