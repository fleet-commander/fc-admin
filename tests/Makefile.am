TESTS_ENVIRONMENT = PYTHONPATH=$(abs_top_srcdir)/tools ; export PYTHONPATH; PATH=$(abs_top_srcdir)/tests/tools:$(PATH) ; export PATH; export FC_TESTING=true; export GJS_PATH=$(abs_top_srcdir)/tools; export GSETTINGS_SCHEMA_DIR=$(abs_top_srcdir)/tests/data;
TESTS = 00_controller.py 01_logger.sh

01_logger.sh: data/gschemas.compiled

data/gschemas.compiled: data/test.gschema.xml
	glib-compile-schemas $(abs_top_srcdir)/tests/data

CLEANFILES = data/gschema.compiled

EXTRA_DIST = \
	00_controller.py         \
	01_logger.sh             \
	_01_mock_dbus.py         \
	_01_logger_test_suite.js \
	data/test.gschema.xml    \
	tools/systemctl
