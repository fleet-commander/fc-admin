Name:           fleet-commander-admin
Version:        0.1
Release:        1%{?dist}
Summary:        Admin interface for Fleet Commander
BuildArch: noarch

License: LGPL-2.1+
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.gz

%define systemd_dir %{_prefix}/lib/systemd/system

%description
Admin interface for Fleet Commander

%package -n fleet-commander-vnc-session
Summary: VNC logger session service for Fleet Commander
Requires: fleet-commander-logger
Requires: systemd
Requires: xorg-x11-server-utils
Requires: gnome-session
Requires: tigervnc-server

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

%pre
getent passwd fleet-commander-admin >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander-admin -s /usr/bin/false -c "Fleet Commander administration interface service" fleet-commander-admin

%pre -n fleet-commander-logger
getent passwd fleet-commander >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander -s /bin/bash -c "Fleet Commander" fleet-commander
exit 0


%files
%defattr(755, root, root)
%{_datadir}
%{_datadir}/fleet-commander-admin
%{_datadir}/fleet-commander-admin/js
%attr(644, -, -) %{_datadir}/fleet-commander-admin/js/*js
%{_datadir}/fleet-commander-admin/js/noVNC/include
%attr(644, -, -) %{_datadir}/fleet-commander-admin/js/noVNC/include/*js
%{_datadir}/fleet-commander-admin/css
%attr(644, -, -) %{_datadir}/fleet-commander-admin/css/*.css
%{_datadir}/fleet-commander-admin/templates
%attr(644, -, -) %{_datadir}/fleet-commander-admin/templates/*.html

%{_libexecdir}
%{_libexecdir}/fleet-commander-admin.py

%{_localstatedir}
%{_localstatedir}/lib
%attr(-, fleet-commander-admin, -) %{_localstatedir}/lib/fleet-commander-admin


%files -n fleet-commander-logger
%defattr(755, root, root) 
%{_libexecdir}
%{_libexecdir}/fleet-commander-logger.py
%{_sysconfdir}/xdg
%{_localstatedir}/lib
%defattr(755, fleet-commander, users) 
%{_localstatedir}/lib/fleet-commander
%{_localstatedir}/lib/fleet-commander/.config
%{_localstatedir}/lib/fleet-commander/.config/autostart
%attr(644, -, -) %{_localstatedir}/lib/fleet-commander/.bashrc
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-logger.conf
%attr(644, -, -) %{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop

%files -n fleet-commander-vnc-session
%defattr(755, root, root)
%{_libexecdir}
%{_libexecdir}/fleet-commander-xvnc.sh
%{_libexecdir}/fleet-commander-xinitrc.sh

%attr(644, root, root) %{systemd_dir}/fleet-commander-vnc-session.service
%changelog
