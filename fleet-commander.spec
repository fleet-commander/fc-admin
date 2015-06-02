Name:           fleet-commander
Version:        0.1
Release:        1%{?dist}
Summary:        Fleet Commander

BuildRequires:  python3-gobject
BuildRequires:  tigervnc-server-minimal
BuildRequires:  dconf
BuildRequires:  systemd

BuildArch: noarch

License: LGPL-2.1+
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.gz

%define systemd_dir %{_prefix}/lib/systemd/system

%description
Admin interface for Fleet Commander

%package -n fleet-commander-admin
Summary: Fleet Commander web interface
Requires: python3
Requires: python3-flask
Requires: systemd
Requires(preun): systemd


%description -n fleet-commander-admin
Fleet Commander web interface to create and deploy profiles

%package -n fleet-commander-vnc-session
Summary: VNC logger session service for Fleet Commander
Requires: fleet-commander-logger
Requires: xorg-x11-server-utils
Requires: gnome-session
Requires: tigervnc-server
Requires: systemd
Requires(preun): systemd

%description -n fleet-commander-vnc-session
Starts a GNOME session inside an Xvnc server with a special user to be accessed by the Fleet Commander admin UI

%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
Requires: python3-gobject
Requires: json-glib
%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions 

%prep
%setup -q
%build
%configure --with-systemdsystemunitdir=%{systemd_dir}
make

%install
%make_install
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart
install -m 644 data/fleet-commander-logger.desktop %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop
ln -s %{_sysconfdir}/bashrc %{buildroot}/%{_localstatedir}/lib/fleet-commander/.bashrc

install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin

%clean
rm -rf %{buildroot}

%pre -n fleet-commander-admin
getent passwd fleet-commander-admin >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander-admin -s /usr/bin/false -c "Fleet Commander administration interface service" fleet-commander-admin

%pre -n fleet-commander-logger
getent passwd fleet-commander >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander -s /bin/bash -c "Fleet Commander" fleet-commander
exit 0

%preun -n fleet-commander-vnc-session
%systemd_preun fleet-commander-vnc-session.service
%systemd_preun fleet-commander-controller.service

%preun -n fleet-commander-admin
%systemd_preun fleet-commander-admin.service

%files -n fleet-commander-admin
%defattr(644, root, root)
%{_datadir}/fleet-commander-admin/js/*js
%{_datadir}/fleet-commander-admin/js/noVNC/include/*js
%{_datadir}/fleet-commander-admin/img/*.png
%{_datadir}/fleet-commander-admin/img/*.svg
%{_datadir}/fleet-commander-admin/img/*.ico
%{_datadir}/fleet-commander-admin/img/*.gif
%{_datadir}/fleet-commander-admin/css/*.css
%{_datadir}/fleet-commander-admin/templates/*.html
%attr(755, -, -) %{_libexecdir}/fleet-commander-admin.py
%exclude %{_libexecdir}/fleet-commander-admin.pyc
%exclude %{_libexecdir}/fleet-commander-admin.pyo
%attr(755, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-admin.conf
%{systemd_dir}/fleet-commander-admin.service

%files -n fleet-commander-logger
%defattr(755, root, root) 

%{_libexecdir}/fleet-commander-logger.py
%exclude %{_libexecdir}/fleet-commander-logger.pyc
%exclude %{_libexecdir}/fleet-commander-logger.pyo
%attr(755, fleet-commander, users) %{_localstatedir}/lib/fleet-commander
%attr(644, root, root) %{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop
%exclude %{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%{_localstatedir}/lib/fleet-commander/.bashrc
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-logger.conf

%files -n fleet-commander-vnc-session
%defattr(755, root, root)
%{_libexecdir}/fleet-commander-xvnc.sh
%{_libexecdir}/fleet-commander-xinitrc.sh
%{_libexecdir}/fleet-commander-controller.py

%exclude %{_libexecdir}/fleet-commander-controller.pyc
%exclude %{_libexecdir}/fleet-commander-controller.pyo

%attr(644, root, root) %{systemd_dir}/fleet-commander-vnc-session.service
%attr(644, root, root) %{systemd_dir}/fleet-commander-controller.service

%changelog
