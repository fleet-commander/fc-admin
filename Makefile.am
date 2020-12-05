RPMBUILD ?= $(abs_builddir)/rpmbuild
TARBALL = $(PACKAGE)-$(VERSION).tar.xz
NULL =

DISTCHECK_CONFIGURE_FLAGS = \
			      --with-systemdsystemunitdir=$$dc_install_base/$(systemdsystemunitdir)
SUBDIRS = data logger admin tests

EXTRA_DIST = \
 	$(wildcard LICENSE.*)                  \
 	$(wildcard COPYING.*)

GENERATED_PYTHON_FILES = \
	admin/fleetcommander/constants.py                  \
	$(NULL)

.PHONY: prep_src rpmroot rpmdistdir rpms

prep_src: rpmroot dist-xz
	cp "$(top_builddir)/$(TARBALL)" "$(RPMBUILD)/SOURCES/"

rpms: prep_src rpmroot rpmdistdir
	rpmbuild \
	    --define "_topdir $(RPMBUILD)" \
	    -ba \
	    "$(top_builddir)/$(PACKAGE).spec"
	cp "$(RPMBUILD)"/RPMS/*/*.rpm "$(top_builddir)/dist/rpms/"
	cp "$(RPMBUILD)"/SRPMS/*.src.rpm "$(top_builddir)/dist/srpms/"

rpmroot:
	mkdir -p "$(RPMBUILD)/BUILD"
	mkdir -p "$(RPMBUILD)/RPMS"
	mkdir -p "$(RPMBUILD)/SOURCES"
	mkdir -p "$(RPMBUILD)/SPECS"
	mkdir -p "$(RPMBUILD)/SRPMS"

rpmdistdir:
	mkdir -p "$(top_builddir)/dist/rpms"
	mkdir -p "$(top_builddir)/dist/srpms"

clean-local:
	rm -rf "$(RPMBUILD)"
	rm -rf "$(top_builddir)/dist"
	rm -f "$(top_builddir)"/$(PACKAGE)-*.tar.gz

.PHONY: pylint
pylint: $(GENERATED_PYTHON_FILES)
	FILES=`find $(top_srcdir) \
	      -type d -exec test -e '{}/__init__.py' \; -print -prune -o \
	      -path './rpmbuild' -prune -o \
	      -name '*.py' -print`; \
	echo -e "Pylinting files:\n$${FILES}\n"; \
	$(PYTHON) -m pylint --version; \
	PYTHONPATH=$(top_srcdir):$(top_srcdir)/admin $(PYTHON) -m pylint \
		--rcfile=$(top_srcdir)/pylintrc \
		--load-plugins pylint_plugins \
		$${FILES}

.PHONY: black
black: $(GENERATED_PYTHON_FILES)
	$(PYTHON) -m black -v \
	    $(top_srcdir)

.PHONY: blackcheck
blackcheck: $(GENERATED_PYTHON_FILES)
	$(PYTHON) -m black -v --check --diff \
	    $(top_srcdir)

.PHONY: eslint
eslint:
	cd admin/cockpit/fleet-commander-admin; \
	npm install; \
	npm run eslint

.PHONY: eslint-fix
eslint-fix:
	cd admin/cockpit/fleet-commander-admin; \
	npm install; \
	npm run eslint:fix
