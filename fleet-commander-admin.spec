Name:           fleet-commander-admin
Version:        0.1
Release:        1%{?dist}
Summary:        Admin interface for Fleet Commander
BuildArch: noarch

License: LGPL-2.1+
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.gz

%description
Admin interface for Fleet Commander

%package -n fleet-commander-logger
Summary:        Logs configuration changes in a session
Requires: python3-gobject
Requires: json-glib
%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions 

%prep
%setup -q
%build
%configure
make

%install
install -m 755 -d %{buildroot}/%{_libexecdir}
install -m 755 tools/fleet-commander-logger.py %{buildroot}/%{_libexecdir}/fleet-commander-logger

install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart
ln -s %{_sysconfdir}/bashrc %{buildroot}/%{_localstatedir}/lib/fleet-commander/.bashrc
install -m 644 data/fleet-commander-logger.desktop %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop

install -m 755 -d %{buildroot}/%{_sysconfdir}/xdg
install -m 644 data/fleet-commander-logger.conf %{buildroot}/%{_sysconfdir}/xdg/fleet-commander-logger.conf

%clean
rm -rf %{buildroot}

%pre -n fleet-commander-logger
getent passwd fleet-commander >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander -s /sbin/nologin -c "Fleet Commander" fleet-commander
exit 0

%files -n fleet-commander-logger
%defattr(755, root, root) 
%{_libexecdir}
%{_libexecdir}/fleet-commander-logger
%{_sysconfdir}/xdg
%{_localstatedir}/lib
%defattr(755, fleet-commander, users) 
%{_localstatedir}/lib/fleet-commander
%{_localstatedir}/lib/fleet-commander/.config
%{_localstatedir}/lib/fleet-commander/.config/autostart
%attr(644, -, -) %{_localstatedir}/lib/fleet-commander/.bashrc
%attr(644, -, -) %{_sysconfdir}/xdg/fleet-commander-logger.conf
%attr(644, -, -) %{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop

%changelog
