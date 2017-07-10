Name:           fleet-commander-admin
Version:        0.9.1
Release:        1%{?dist}
Summary:        Fleet Commander

BuildArch: noarch

License: LGPLv3+ and LGPLv2+ and MIT and BSD
URL: https://raw.githubusercontent.com/fleet-commander/fc-admin/master/fleet-commander-admin.spec
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.xz

BuildRequires: python2-devel
BuildRequires: dbus-python
BuildRequires: pygobject2
BuildRequires: libvirt-python
BuildRequires: python-dbusmock
BuildRequires: gjs
BuildRequires: dconf
BuildRequires: desktop-file-utils
%if 0%{?rhel} < 8
BuildRequires: pexpect
BuildRequires: pygobject3
%endif
%if 0%{?fedora} >= 21
BuildRequires: python2-pexpect
BuildRequires: python-gobject
%endif

Requires: NetworkManager
Requires: NetworkManager-libnm
Requires: systemd
Requires: dconf
Requires: python2
Requires: dbus-python
Requires: pygobject2
Requires: libvirt-python
Requires: cockpit
Requires(preun): systemd
%if 0%{?rhel} < 8
Requires: pexpect
Requires: pygobject3
%endif
%if 0%{?fedora} >= 21
Requires: python2-pexpect
Requires: python-gobject
%endif

Provides: bundled(spice-html5)

%description
Fleet Commander is an application that allows you to manage the desktop
configuration of a large network of users and workstations/laptops.

%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
License: GPLv2
Requires: gjs
Requires: libsoup
Requires: json-glib

%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions. Fleet Commander is an
application that allows you to manage the desktop configuration of a large
network of users and workstations/laptops.

%prep
%setup -q

%check
desktop-file-validate %{buildroot}/%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%build
%configure --with-systemdsystemunitdir=%{_unitdir}
%make_build

%install
%make_install
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin/profiles

%files
%license
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}/python
%dir %{_datadir}/%{name}/python/fleetcommander
%{_datadir}/cockpit/fleet-commander-admin
%{_datadir}/%{name}/fc-goa-providers.ini
%attr(644, -, -) %{_datadir}/%{name}/python/fleetcommander/*.py
%attr(644, -, -) %{_datadir}/%{name}/python/fleetcommander/*.py[co]
%config(noreplace) %{_sysconfdir}/xdg/%{name}.conf
%{_datadir}/dbus-1/services/org.freedesktop.FleetCommander.service
%{_localstatedir}/lib/%{name}
%attr(755, root, root) %{_libexecdir}/fleet-commander-admin

%files -n fleet-commander-logger
%attr(755, root, root) %{_libexecdir}/fleet_commander_logger.js
%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop
%{_sysconfdir}/udev/rules.d/81-fleet-commander-logger.rules

%changelog
* Mon Jul 10 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.9.1-1
- Updated package for 0.10.0 release

* Mon Feb 20 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.9.0-1
- Updated package for 0.9.0 release

* Fri Sep 16 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.8.0-1
- Updated package for 0.8.0 release

* Fri Sep 16 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.99-5
- Removed patternfly and jquery from bundled provides

* Fri Sep 16 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.99-4
- Fixed changelog formatting and typos in email address

* Fri Sep 16 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.99-3
- Removed unneeded permission for fleet-commander-admin user

* Thu Sep 08 2016 Alberto Ruiz <aruizrui@redhat.com> - 0.7.99-2
- Update licensing metadata

* Mon Jun 06 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.99-1
- Fleet Commander admin migrated to Cockpit plugin
- Updated package for 0.7.99 release

* Thu Apr 07 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.6-1
- Created workaround for libvirt bug dealing with too large qemu monitor paths
- Updated package for 0.7.6 release

* Thu Mar 31 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.5-1
- Fixed spice reconnection problems
- Updated package for 0.7.5 release

* Tue Mar 08 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.4-1
- Update package for 0.7.4 release

* Fri Feb 05 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.3-2
- Removed failing tests

* Fri Feb 05 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.3-1
- Fixes in spec for Fedora release

* Thu Jan 28 2016 Oliver Gutierrez <ogutierrez@redhat.com> - 0.7.2-1
- Fixes in spec for Fedora release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.com> - 0.7.1-1
- Update package for 0.7.1 release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.com> - 0.7.0-1
- Update package for 0.7.0 release

* Wed Jan 13 2016 Alberto Ruiz <aruiz@redhat.com> - 0.2.0-1
- Initial RPM release
