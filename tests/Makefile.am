TESTS_ENVIRONMENT = export PATH=$(abs_top_srcdir)/tests/tools:$(PATH); export TOPSRCDIR=$(abs_top_srcdir); export GJS_PATH=$(abs_top_srcdir)/tools; export FC_TESTING=true;
TESTS = 00_controller.py 01_logger_gsettings.sh 02_logger_connmgr.js 03_logger_goa.js 04_admin.py

EXTRA_DIST = \
	$(TESTS)                 \
	_01_mock_dbus.py         \
	_01_logger_test_suite.js \
	data/test.gschema.xml    \
	tools/websockify         \
	tools/systemctl
