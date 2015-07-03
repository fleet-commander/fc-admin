TESTS_ENVIRONMENT = PYTHONPATH=$(abs_top_srcdir)/tools ; export PYTHONPATH; PATH=$(abs_top_srcdir)/tests/tools:$(PATH) ; export PATH; export FC_TESTING=true; export GJS_PATH=$(abs_top_srcdir)/tools; export GSETTINGS_SCHEMA_DIR=$(abs_top_srcdir)/tests/data;
TESTS = 00_controller.py 01_logger.sh

01_logger.sh: data/gschemas.compiled

data/gschemas.compiled: data/test.gschema.xml
	glib-compile-schemas $(abs_top_srcdir)/data

CLEANFILES = data/gschema.compiled

EXTRA_DIST = \
	00_controller.py         \
	01_logger.sh             \
	01__mock_dbus.py         \
	01__logger_test_suite.js \
	mock_dbus.py             \
	data/test.gschema.xml    \
	tools/systemctl
