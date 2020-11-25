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

AstroidBuilder(MANAGER).string_build(
    textwrap.dedent(
        """\
        import unittest
        from tests.test_libvirt_controller import TestLibVirtController

        TestLibVirtController.assertTrue = unittest.TestCase.assertTrue
        TestLibVirtController.assertFalse = unittest.TestCase.assertFalse
        TestLibVirtController.assertEqual = unittest.TestCase.assertEqual
        TestLibVirtController.assertListEqual = unittest.TestCase.assertListEqual
        TestLibVirtController.assertDictEqual = unittest.TestCase.assertDictEqual
        """
    )
)
