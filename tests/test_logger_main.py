#!/usr/bin/env python-wrapper.sh

#
# Copyright (C) 2022  FleetCommander Contributors see COPYING for license
#

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch, mock_open
import logging
import unittest

from fleet_commander_logger import DEFAULT_SPICE_CHANNEL_DEV as spice_device
from fleet_commander_logger import LOG_DEVICE as log_device
import fleet_commander_logger as fc_logger

logger = logging.getLogger(Path(__file__).name)


def device_exists_side_effect(exists_dict):
    def _exists(path):
        return exists_dict[path]

    return _exists


class TestLoggerMain(unittest.TestCase):
    def setUp(self):
        # writing to nonexistent log device
        self.open_patcher = patch.object(fc_logger, "open", mock_open())
        self.mock_open = self.open_patcher.start()

        self.device_exists_patcher = patch("fleet_commander_logger.device_exists")
        self.mock_exists = self.device_exists_patcher.start()

        self.fclogger_patcher = patch("fleet_commander_logger.FleetCommanderLogger")
        self.mock_fclogger = self.fclogger_patcher.start()

        self.basicConfig_patcher = patch.object(fc_logger.logging, "basicConfig")
        self.mock_basicConfig = self.basicConfig_patcher.start()

    def tearDown(self):
        self.basicConfig_patcher.stop()
        self.fclogger_patcher.stop()
        self.device_exists_patcher.stop()
        self.open_patcher.stop()

    def test_help(self):
        """Check help message"""
        out = StringIO()
        err = StringIO()
        with self.assertRaises(SystemExit) as cm, redirect_stdout(out), redirect_stderr(
            err
        ):
            fc_logger.main(["--help"])

        self.assertEqual(cm.exception.code, 0)
        self.assertIn(f"usage: {Path(fc_logger.__file__).name} ", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def assert_called_with_handlers(self, *expected_handlers):
        # assert_called_once_with doesn't help here due to complexity of objects
        # checking manually
        self.mock_basicConfig.assert_called_once()
        # args
        self.assertEqual(self.mock_basicConfig.call_args.args, ())
        # kwargs
        kwargs = self.mock_basicConfig.call_args.kwargs
        self.assertEqual(len(kwargs), 2, msg=f"basicConfig was called with: {kwargs}")
        ## handlers
        actual_handlers = kwargs["handlers"]
        self.assertEqual(len(actual_handlers), len(expected_handlers))
        for expected_handler, actual_handler in zip(expected_handlers, actual_handlers):
            expected_type, expected_level = expected_handler
            self.assertIsInstance(actual_handler, expected_type)
            self.assertEqual(
                actual_handler.level,
                expected_level,
                msg=f"Logging level differs for handler: {actual_handler}",
            )

        ## root logger level
        self.assertEqual(kwargs["level"], logging.DEBUG)

    def test_verbose_logging_existent_log_device(self):
        """Check logging in verbose mode if log device exists"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: True, log_device: True}
        )
        aliases = ["-v", "--verbose", "-d", "--debug"]

        for alias in aliases:
            fc_logger.main([alias])
            self.assert_called_with_handlers(
                (fc_logger.LoggerStreamHandler, logging.DEBUG),
                (logging.StreamHandler, logging.DEBUG),
            )
            # reset calls
            self.mock_basicConfig.reset_mock()

    def test_verbose_logging_nonexistent_log_device(self):
        """Check logging in verbose mode if log device doesn't exist"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: True, log_device: False}
        )
        aliases = ["-v", "--verbose", "-d", "--debug"]

        for alias in aliases:
            fc_logger.main([alias])
            self.assert_called_with_handlers((logging.StreamHandler, logging.DEBUG))
            # reset calls
            self.mock_basicConfig.reset_mock()

    def test_nonverbose_logging_nonexistent_log_device(self):
        """Check logging in non verbose mode if log device doesn't exist"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: True, log_device: False}
        )
        fc_logger.main([])
        self.assert_called_with_handlers((logging.StreamHandler, logging.WARNING))

    def test_nonverbose_logging_existent_log_device(self):
        """Check logging in non verbose mode if log device exists"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: True, log_device: True}
        )
        fc_logger.main([])
        self.assert_called_with_handlers(
            (fc_logger.LoggerStreamHandler, logging.DEBUG),
            (logging.StreamHandler, logging.WARNING),
        )

    def test_no_devfile(self):
        """Check --no-devfile"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: False, log_device: False}
        )
        fc_logger.main(["--no-devfile"])
        self.mock_fclogger.assert_called_once_with(use_device_file=False)

    def test_missing_spice_device(self):
        """Check missing spice device"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: False, log_device: False}
        )
        with self.assertRaises(SystemExit) as cm, self.assertLogs(
            fc_logger.logger, level="ERROR"
        ) as lcm:
            fc_logger.main([])

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Neither --no-devfile was specified nor device", lcm.output[0])
        self.mock_fclogger.assert_not_called()

    def test_spice_device(self):
        """Check default usage"""
        self.mock_exists.side_effect = device_exists_side_effect(
            {spice_device: True, log_device: False}
        )
        fc_logger.main([])
        self.mock_fclogger.assert_called_once_with(use_device_file=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main(verbosity=2)
