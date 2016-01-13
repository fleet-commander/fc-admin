TESTS_ENVIRONMENT = export PATH=$(abs_top_srcdir)/tests/tools:$(PATH); export TOPSRCDIR=$(abs_top_srcdir); export GJS_PATH=$(abs_top_srcdir)/logger; export FC_TESTING=true;
TESTS = 00_database.py 01_logger_dconf.sh 02_logger_connmgr.js 03_logger_goa.js 04_libvirt_controller.py 05_fcdbus.py 06_logger_devfile.js 07_admin.py

EXTRA_DIST =                         \
	$(TESTS)                         \
	libvirtmock.py                   \
	_01_mock_dbus.py                 \
	_01_logger_test_suite.js         \
	data/test.gschema.xml            \
	data/libvirt_domain-orig.xml     \
	data/libvirt_domain-modified.xml \
	data/libvirt_domain-nospice.xml  \
	tools/websockify                 \
	tools/systemctl                  \
	tools/ssh                        \
	tools/ssh-keyscan                \
	tools/ip
