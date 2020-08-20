RPMBUILD ?= $(abs_builddir)/rpmbuild
TARBALL = $(PACKAGE)-$(VERSION).tar.xz

DISTCHECK_CONFIGURE_FLAGS = \
			      --with-systemdsystemunitdir=$$dc_install_base/$(systemdsystemunitdir)
SUBDIRS = data logger admin tests

EXTRA_DIST = \
 	$(wildcard LICENSE.*)                  \
 	$(wildcard COPYING.*)

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
