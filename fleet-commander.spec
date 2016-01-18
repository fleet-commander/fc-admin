Name:           fleet-commander
Version:        0.2.0
Release:        1%{?dist}
Summary:        Fleet Commander

BuildArch: noarch

License: LGPLv2+ and MIT and BSD and ASL 2.0 and OFL
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.xz

%define systemd_dir %{_prefix}/lib/systemd/system

%description
Admin interface for Fleet Commander

%package -n fleet-commander-admin
Summary: Fleet Commander web interface
Requires: systemd
Requires: dconf
Requires: python
Requires: dbus-python
Requires: pygobject2
Requires: libvirt-python
Requires: python-websockify
Requires: python-crypto
Requires(preun): systemd

%description -n fleet-commander-admin
Fleet Commander web interface to create and deploy profiles

%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
Requires: gjs
Requires: typelib(Soup-2.4)
Requires: typelib(Json-1.0)

%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions

%package -n fleet-commander-apache
Summary: Fleet Commander apache integration
Requires: httpd-filesystem
Requires: mod_wsgi
Requires: fleet-commander-admin
Requires(preun): systemd

%description -n fleet-commander-apache
Fleet commander integration with Apache web server

%prep
%setup -q
%build
%configure --with-systemdsystemunitdir=%{_unitdir}
make

%install
%make_install
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin/profiles

%clean
rm -rf %{buildroot}

%pre -n fleet-commander-admin
getent passwd fleet-commander-admin >/dev/null || /usr/sbin/useradd -M -r -d %{_localstatedir}/lib/fleet-commander-admin -s /usr/bin/false -c "Fleet Commander administration interface service" fleet-commander-admin

%preun -n fleet-commander-admin
%systemd_preun fleet-commander-admin.service
%systemd_preun fleet-commander-dbus.service

%files -n fleet-commander-admin
%defattr(644, root, root)
%{_datadir}/fleet-commander-admin/js/*js
%{_datadir}/fleet-commander-admin/js/spice-html5/*js
%{_datadir}/fleet-commander-admin/js/spice-html5/thirdparty/*js
%{_datadir}/fleet-commander-admin/img/*.png
%{_datadir}/fleet-commander-admin/img/*.svg
%{_datadir}/fleet-commander-admin/img/*.ico
%{_datadir}/fleet-commander-admin/img/*.gif
%{_datadir}/fleet-commander-admin/css/*.css
%{_datadir}/fleet-commander-admin/templates/*.html
%{_datadir}/fleet-commander-admin/fonts/*.ttf
%{_datadir}/fleet-commander-admin/fonts/*.woff
%{_datadir}/fleet-commander-admin/fonts/*.eot
%{_datadir}/fleet-commander-admin/fonts/*.svg
%{_datadir}/fleet-commander-admin/fonts/*.woff2
%{_libdir}/fleet-commander/fleetcommander/__init__.py
%{_libdir}/fleet-commander/fleetcommander/__init__.py[co]
%{_libdir}/fleet-commander/fleetcommander/admin.py
%{_libdir}/fleet-commander/fleetcommander/admin.py[co]
%{_libdir}/fleet-commander/fleetcommander/collectors.py
%{_libdir}/fleet-commander/fleetcommander/collectors.py[co]
%{_libdir}/fleet-commander/fleetcommander/database.py
%{_libdir}/fleet-commander/fleetcommander/database.py[co]
%{_libdir}/fleet-commander/fleetcommander/fcdbus.py
%{_libdir}/fleet-commander/fleetcommander/fcdbus.py[co]
%{_libdir}/fleet-commander/fleetcommander/flaskless.py
%{_libdir}/fleet-commander/fleetcommander/flaskless.py[co]
%{_libdir}/fleet-commander/fleetcommander/libvirtcontroller.py
%{_libdir}/fleet-commander/fleetcommander/libvirtcontroller.py[co]
%{_libdir}/fleet-commander/fleetcommander/utils.py
%{_libdir}/fleet-commander/fleetcommander/utils.py[co]
%config(noreplace) %{_sysconfdir}/xdg/fleet-commander-admin.conf
%config %{_sysconfdir}/dbus-1/system.d/org.freedesktop.FleetCommander.conf
%{_unitdir}/fleet-commander-admin.service
%{_unitdir}/fleet-commander-dbus.service
%{_datadir}/dbus-1/system-services/org.freedesktop.FleetCommander.service
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin/profiles

%files -n fleet-commander-logger
%defattr(755, root, root)
%{_libexecdir}/fleet_commander_logger.js
%attr(755, root, root) %{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%files -n fleet-commander-apache
%defattr(644, root, root)
%config(noreplace) %{_sysconfdir}/xdg/fleet-commander-apache.conf
%attr(755, -, -) %{_libexecdir}/admin.wsgi

%post -n fleet-commander-apache
semanage port -a -t http_port_t -p tcp 8182; semanage port -a -t http_port_t -p tcp 8989; semanage fcontext -a -t httpd_var_lib_t '/var/lib/fleet-commander-admin/database.db'; restorecon -v '/var/lib/fleet-commander-admin/database.db'

%changelog
* Wed Jan 13 2016 Alberto Ruiz <aruiz@redhat.com> - 0.2.0-1
- Initial RPM release
