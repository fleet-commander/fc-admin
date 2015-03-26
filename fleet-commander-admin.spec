Name:           fleet-commander-admin
Version:        0.1
Release:        1%{?dist}
Summary:        Admin interface for Fleet Commander
BuildArch: noarch

License: LGPL-2.1+
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.gz

Requires: python3-gobject
Requires: json-glib

%description
Admin interface for Fleet Commander


%package -n fleet-commander-logger
Summary:        Logs configuration changes in a session
%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions 


%prep
%setup -q
%build
%configure
make

%pre -n fleet-commander-logger
getent passwd fleet-commander >/dev/null || /usr/sbin/useradd -r -g users -d %{_localstatedir}/lib/fleet-commander -s /sbin/nologin -c "Fleet Commander" fleet-commander
exit 0

%install
install -m 755 -d %{buildroot}/%{_libexecdir}
install -m 755 tools/fleet-commander-logger.py %{buildroot}/%{_libexecdir}/fleet-commander-logger

install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart
install -m 755 data/fleet-commander-logger.desktop %{buildroot}/%{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop

%clean
rm -rf %{buildroot}

%files -n fleet-commander-logger
%attr(755, root, root) %{_libexecdir}
%attr(755, root, root) %{_libexecdir}/fleet-commander-logger

%attr(755, root, root) %{_localstatedir}/lib
%attr(755, fleet-commander, users) %{_localstatedir}/lib/fleet-commander
%attr(755, fleet-commander, users) %{_localstatedir}/lib/fleet-commander/.config
%attr(755, fleet-commander, users) %{_localstatedir}/lib/fleet-commander/.config/autostart
%attr(644, fleet-commander, users) %{_localstatedir}/lib/fleet-commander/.config/autostart/fleet-commander-logger.desktop

%changelog
