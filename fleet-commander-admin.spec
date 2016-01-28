Name:           fleet-commander-admin
Version:        0.7.1
Release:        2%{?dist}
Summary:        Fleet Commander

BuildArch: noarch

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

%description
Fleet Commander is an application that allows you to manage the desktop
configuration of a large network of users and workstations/laptops.

Requires: systemd
Requires: dconf
Requires: python
Requires: dbus-python
Requires: pygobject2
Requires: libvirt-python
Requires: python-websockify

Requires: python-crypto
Requires: numpy

Requires: httpd
Requires: mod_wsgi
Requires(preun): systemd

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
%attr(755, fleet-commander-admin, -) %{_datadir}/fleet-commander-admin/

#%{_datadir}/fleet-commander-admin/appdata/static/js/*js
#%{_datadir}/fleet-commander-admin/appdata/static/js/spice-html5/*js
#%{_datadir}/fleet-commander-admin/appdata/static/js/spice-html5/thirdparty/*js
#%{_datadir}/fleet-commander-admin/appdata/static/img/*.png
#%{_datadir}/fleet-commander-admin/appdata/static/img/*.svg
#%{_datadir}/fleet-commander-admin/appdata/static/img/*.ico
#%{_datadir}/fleet-commander-admin/appdata/static/img/*.gif
#%{_datadir}/fleet-commander-admin/appdata/static/css/*.css
#%{_datadir}/fleet-commander-admin/appdata/templates/*.html
#%{_datadir}/fleet-commander-admin/appdata/static/fonts/*.ttf
#%{_datadir}/fleet-commander-admin/appdata/static/fonts/*.woff
#%{_datadir}/fleet-commander-admin/appdata/static/fonts/*.eot
#%{_datadir}/fleet-commander-admin/appdata/static/fonts/*.svg
#%{_datadir}/fleet-commander-admin/appdata/static/fonts/*.woff2
#%{_datadir}/fleet-commander-admin/python/fleetcommander/__init__.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/__init__.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/admin.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/admin.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/collectors.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/collectors.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/database.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/database.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/fcdbus.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/fcdbus.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/flaskless.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/flaskless.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/libvirtcontroller.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/libvirtcontroller.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/utils.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/utils.py[co]
#%{_datadir}/fleet-commander-admin/python/fleetcommander/constants.py
#%{_datadir}/fleet-commander-admin/python/fleetcommander/constants.py[co]

%config(noreplace) %attr(644, fleet-commander-admin, -) %{_sysconfdir}/xdg/fleet-commander-admin.conf
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/org.freedesktop.FleetCommander.conf
%{_unitdir}/fleet-commander-dbus.service
%{_datadir}/dbus-1/system-services/org.freedesktop.FleetCommander.service
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin
%attr(755, -, -) %{_prefix}/bin/fleet-commander-standalone
%config(noreplace) %{_sysconfdir}/xdg/fleet-commander-apache.conf
%attr(755, -, -) %{_libexecdir}/admin.wsgi

%files -n fleet-commander-logger
%attr(755, root, root) %{_libexecdir}/fleet_commander_logger.js
%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%changelog
* Thu Jan 28 2016 Oliver Gurierrez <ogutierrez@redhat.org> - 0.7.1-2
- Fixes in spec for Fedora release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.org> - 0.7.1-1
- Update package for 0.7.1 release

* Tue Jan 19 2016 Alberto Ruiz <aruiz@redhat.org> - 0.7.0-1
- Update package for 0.7.0 release

* Wed Jan 13 2016 Alberto Ruiz <aruiz@redhat.com> - 0.2.0-1
- Initial RPM release
