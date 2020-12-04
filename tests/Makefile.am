NULL =

TESTS_ENVIRONMENT = \
	export PATH=$(abs_top_srcdir)/tests/tools:$(abs_top_srcdir)/tests:$(PATH); \
	export TOPSRCDIR=$(abs_top_srcdir); \
	export FC_TESTING=true; \
	export XDG_DATA_DIRS=$(abs_top_srcdir)/tests/data/; \
	export PYTHON=@PYTHON@; \
	export PYTHONPATH=$(abs_top_srcdir):$(abs_top_srcdir)/admin; \
	export PYTHONPATH=$${PYTHONPATH}:$(abs_top_srcdir)/logger; \
	$(NULL)

TESTS = \
	test_database.py \
	test_freeipa.py \
	test_fcad.py \
	test_sshcontroller.py \
	test_mergers.py \
	test_logger_dconf.sh \
	test_logger_connmgr.py \
	test_logger_nm.sh \
	test_logger_chromium.py \
	test_logger_firefox.py \
	test_libvirt_controller.py \
	test_fcdbus.sh \
	$(NULL)

EXTRA_DIST =                         \
	$(TESTS)                         \
	__init__.py                      \
	python-wrapper.sh                \
	freeipamock.py                   \
	libvirtmock.py                   \
	ldapmock.py                      \
	smbmock.py                       \
	directorymock.py                 \
	fcdbusclient.py                  \
	_mock_dbus.py                    \
	_logger_test_suite.py            \
	_wait_for_name.py                \
	_logger_nm.py                    \
	_mock_nm_dbus.py                 \
	_fcdbus_tests.py                 \
	_mock_realmd_dbus.py             \
	test_fcdbus_service.py           \
	data/test.gschema.xml            \
	data/libvirt_domain-orig.xml     \
	data/libvirt_domain-modified-html5.xml \
	data/libvirt_domain-modified-direct.xml \
	data/libvirt_domain-nospice.xml  \
	data/fc_goa_providers_test.ini   \
	data/fleet-commander-logger/fc-chromium-policies.json   \
	tools/ssh                        \
	tools/ssh-keygen                 \
	tools/ssh-keyscan                \
	tools/ssh-session-mock           \
	$(NULL)
