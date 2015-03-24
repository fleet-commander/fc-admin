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
%install
install -m 755 -d %{buildroot}/%{_libexecdir}
install -m 755 tools/fleet-commander-logger.py %{buildroot}/%{_libexecdir}/fleet-commander-logger

install -m 755 -d %{buildroot}/%{_sysconfdir}/xdg/autostart
install -m 755 data/fleet-commander-logger.desktop %{buildroot}/%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%clean
rm -rf %{buildroot}

%files -n fleet-commander-logger
%{_libexecdir}
%{_sysconfdir}/xdg/autostart
%{_libexecdir}/fleet-commander-logger
%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%doc

%changelog
* Fri Mar 20 2015 Alberto Ruiz <aruiz@redhat.com>
- Initial package
