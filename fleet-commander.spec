Name:           fleet-commander
Version:        0.2.0
Release:        1%{?dist}
Summary:        Fleet Commander

#BuildRequires:  python3-gobject
BuildRequires:  python
BuildRequires:  python-requests
BuildRequires:  dconf
BuildRequires:  systemd

BuildArch: noarch

License: LGPL-2.1+ and MIT and BSD-3-Clause and Apache-2.0 and OFL-1.0
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.xz

%define systemd_dir %{_prefix}/lib/systemd/system

%description
Admin interface for Fleet Commander

%package -n fleet-commander-admin
Summary: Fleet Commander web interface
Requires: python
Requires: python-websockify
Requires: libvirt-python
Requires: systemd
Requires(preun): systemd

%description -n fleet-commander-admin
Fleet Commander web interface to create and deploy profiles

%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
#Requires: python3-gobject
Requires: gjs
Requires: libsoup
Requires: json-glib

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
%configure --with-systemdsystemunitdir=%{systemd_dir}
make

%install
%make_install
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart
install -m 644 data/fleet-commander-logger.desktop %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop
install -m 644 data/gnome-software-service.desktop %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart/gnome-software-service.desktop
install -m 644 data/gnome-initial-setup-done %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/gnome-initial-setup-done
ln -s %{_sysconfdir}/profile %{buildroot}/%{_localstatedir}/lib/fleet-commander/.bash_profile
ln -s %{_sysconfdir}/bashrc %{buildroot}/%{_localstatedir}/lib/fleet-commander/.bashrc
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin/profiles

%clean
rm -rf %{buildroot}

%pre -n fleet-commander-admin
getent passwd fleet-commander-admin >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander-admin -s /usr/bin/false -c "Fleet Commander administration interface service" fleet-commander-admin

%pre -n fleet-commander-logger
getent passwd fleet-commander >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander -s /bin/bash -c "Fleet Commander" fleet-commander
exit 0

%preun -n fleet-commander-admin
%systemd_preun fleet-commander-admin.service

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
%{_libdir}/fleet-commander/fleetcommander/__init__.py
%{_libdir}/fleet-commander/fleetcommander/__init__.py[co]
%{_libdir}/fleet-commander/fleetcommander/admin.py
%{_libdir}/fleet-commander/fleetcommander/admin.py[co]
%{_libdir}/fleet-commander/fleetcommander/collectors.py
%{_libdir}/fleet-commander/fleetcommander/collectors.py[co]
%{_libdir}/fleet-commander/fleetcommander/database.py
%{_libdir}/fleet-commander/fleetcommander/database.py[co]
%{_libdir}/fleet-commander/fleetcommander/flaskless.py
%{_libdir}/fleet-commander/fleetcommander/flaskless.py[co]
%{_libdir}/fleet-commander/fleetcommander/libvirtcontroller.py
%{_libdir}/fleet-commander/fleetcommander/libvirtcontroller.py[co]
%{_libdir}/fleet-commander/fleetcommander/utils.py
%{_libdir}/fleet-commander/fleetcommander/utils.py[co]
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin/profiles
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-admin.conf
%{systemd_dir}/fleet-commander-admin.service

%files -n fleet-commander-logger
%defattr(755, root, root)
%{_libexecdir}/fleet_commander_logger.js
%attr(755, fleet-commander, users) %{_localstatedir}/lib/fleet-commander
%attr(644, root, root) %{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop
%attr(644, root, root) %{_localstatedir}/lib/fleet-commander/.config/autostart/gnome-software-service.desktop
%attr(644, root, root) %{_localstatedir}/lib/fleet-commander/.config/gnome-initial-setup-done
%attr(644, root, root) %{_localstatedir}/lib/fleet-commander/.config/libreoffice/dconfwrite
%exclude %{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop
%exclude %{_sysconfdir}/xdg/autostart/gnome-software-service.desktop
%exclude %{_sysconfdir}/xdg/gnome-initial-setup-done
%{_localstatedir}/lib/fleet-commander/.bash_profile
%{_localstatedir}/lib/fleet-commander/.bashrc
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-logger.conf

%files -n fleet-commander-apache
%defattr(644, root, root)
%{_sysconfdir}/httpd/conf.d/fleet-commander-apache.conf
%{_libdir}/fleet-commander/admin.wsgi

%post -n fleet-commander-apache
semanage port -a -t http_port_t -p tcp 8182; semanage port -a -t http_port_t -p tcp 8989; semanage fcontext -a -t httpd_var_lib_t '/var/lib/fleet-commander-admin/database.db'; restorecon -v '/var/lib/fleet-commander-admin/database.db'

%changelog
