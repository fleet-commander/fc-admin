Name:           fleet-commander-admin
Version:        0.7.5
Release:        1%{?dist}
Summary:        Fleet Commander

BuildArch: noarch

# Fleet commander code is LGPLv2. spice-html5 uses dual license (GPLv3 or LGPLv3)
# Bootstrap and jQuery are MIT licensed and Patternfly is MIT, ASL 2.0 and OFL
License: LGPLv2+ and MIT and BSD and ASL 2.0 and OFL
URL: https://raw.githubusercontent.com/fleet-commander/fc-admin/master/fleet-commander-admin.spec
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.xz

BuildRequires: python2-devel
BuildRequires: dbus-python
BuildRequires: pygobject2
BuildRequires: libvirt-python
BuildRequires: python-websockify
BuildRequires: numpy
BuildRequires: python-crypto
BuildRequires: python-dbusmock
BuildRequires: gjs
BuildRequires: dconf
BuildRequires: desktop-file-utils

Requires: systemd
Requires: dconf
Requires: python2
Requires: dbus-python
Requires: pygobject2
Requires: libvirt-python
Requires: python-websockify
Requires: python-crypto
Requires: numpy
Requires: httpd
Requires: mod_wsgi
Requires(preun): systemd

Provides: bundled(jquery) = 1.11.1
Provides: bundled(patternfly)
Provides: bundled(spice-html5)

%description
Fleet Commander is an application that allows you to manage the desktop
configuration of a large network of users and workstations/laptops.

%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
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

%pre
getent passwd fleet-commander-admin >/dev/null || /usr/sbin/useradd -M -r -d %{_localstatedir}/lib/fleet-commander-admin -s /usr/bin/false -c "Fleet Commander administration interface service" fleet-commander-admin

%preun
%systemd_preun fleet-commander-admin.service
%systemd_preun fleet-commander-dbus.service

%files
%license
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}/appdata
%dir %{_datadir}/%{name}/python
%dir %{_datadir}/%{name}/python/fleetcommander
%{_datadir}/%{name}/appdata
%attr(644, -, -) %{_datadir}/%{name}/python/fleetcommander/*.py
%attr(644, -, -) %{_datadir}/%{name}/python/fleetcommander/*.py[co]
%config(noreplace) %{_sysconfdir}/xdg/%{name}.conf
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/org.freedesktop.FleetCommander.conf
%{_unitdir}/fleet-commander-dbus.service
%{_datadir}/dbus-1/system-services/org.freedesktop.FleetCommander.service
%attr(-, fleet-commander-admin, -) %{_localstatedir}/lib/%{name}
%attr(755, -, -) %{_prefix}/bin/fleet-commander-standalone
%config(noreplace) %{_sysconfdir}/xdg/fleet-commander-apache.conf
%attr(755, -, -) %{_libexecdir}/admin.wsgi

%files -n fleet-commander-logger
%attr(755, root, root) %{_libexecdir}/fleet_commander_logger.js
%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%changelog
* Thu Mar 31 2016 ogutierr <ogutierr@redhat.com> - 0.7.5-1
- Fixed spice reconnection problems
- Updated package for 0.7.5 release

* Tue Mar 08 2016 ogutierr <ogutierrez@redhat.com> - 0.7.4-1
- Update package for 0.7.4 release

* Fri Feb 05 2016 ogutierr <ogutierrez@redhat.com> - 0.7.3-2
- Removed failing tests

* Fri Feb 05 2016 ogutierr - 0.7.3-1
- Fixes in spec for Fedora release

* Thu Jan 28 2016 Oliver Gurierrez <ogutierrez@redhat.org> - 0.7.2-1
- Fixes in spec for Fedora release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.org> - 0.7.1-1
- Update package for 0.7.1 release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.org> - 0.7.0-1
- Update package for 0.7.0 release

* Wed Jan 13 2016 Alberto Ruiz <aruiz@redhat.com> - 0.2.0-1
- Initial RPM release
