Name:           fleet-commander-admin
Version:        0.16.0
Release:        1%{?dist}
Summary:        Fleet Commander

%global python_interpreter python3

BuildArch: noarch

License: LGPLv3+ and LGPLv2+ and MIT and BSD
URL: https://github.com/fleet-commander/fc-admin
Source0: https://github.com/fleet-commander/fc-admin/releases/download/%{version}/%{name}-%{version}.tar.xz

BuildRequires: dconf
BuildRequires: desktop-file-utils
BuildRequires: systemd-devel

BuildRequires: python3-devel
BuildRequires: python3-pexpect
BuildRequires: python3-gobject
BuildRequires: python3-dbus
BuildRequires: python3-libvirt
BuildRequires: python3-samba

%if 0%{?with_check}
BuildRequires: git
BuildRequires: python3-dns
BuildRequires: python3-ldap
BuildRequires: python3-dbusmock
BuildRequires: python3-ipalib
BuildRequires: NetworkManager-libnm
BuildRequires: json-glib
BuildRequires: procps
%endif

Requires: NetworkManager
Requires: NetworkManager-libnm
Requires: systemd
Requires: dconf
Requires: cockpit
Requires(preun): systemd

Requires: python3
Requires: python3-pexpect
Requires: python3-dbus
Requires: python3-gobject
Requires: python3-libvirt
Requires: python3-ipalib >= 4.4.1
Requires: python3-ipaclient >= 4.4.1
Requires: python3-ipa-desktop-profile-client
Requires: python3-dns
Requires: python3-samba
Requires: python3-ldap

Provides: bundled(spice-html5)

%description
Fleet Commander is an application that allows you to manage the desktop
configuration of a large network of users and workstations/laptops.


%package -n fleet-commander-logger
Summary: Logs configuration changes in a session
License: GPLv2


Requires: python3
Requires: python3-gobject
Requires: python3-dbus

%description -n fleet-commander-logger
Logs changes for Fleet Commander virtual sessions. Fleet Commander is an
application that allows you to manage the desktop configuration of a large
network of users and workstations/laptops.

%prep
%setup -q

%check
desktop-file-validate %{buildroot}/%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop

%build
export PYTHON=%{python_interpreter}
%configure
%make_build

%install
%make_install
install -m 755 -d %{buildroot}/%{_localstatedir}/lib/fleet-commander-admin/profiles

%preun
%systemd_preun fleet-commander-admin.service

%post
%systemd_post fleet-commander-admin.service

%postun
%systemd_postun_with_restart fleet-commander-admin.service

%files
%license
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}/python
%dir %{_datadir}/%{name}/python/fleetcommander
%{_datadir}/pixmaps/fc-admin.png
%{_datadir}/cockpit/fleet-commander-admin
%{_datadir}/%{name}/fc-goa-providers.ini
%attr(644, -, -) %{_datadir}/%{name}/python/fleetcommander/*.py
%exclude %{_datadir}/%{name}/python/fleetcommander/*.py[co]
%exclude %{_datadir}/%{name}/python/fleetcommander/__pycache__
%config(noreplace) %{_sysconfdir}/xdg/%{name}.conf
%{_datadir}/dbus-1/services/org.freedesktop.FleetCommander.service
%{_localstatedir}/lib/%{name}
%attr(755, -, -) %{_libexecdir}/fleet-commander-admin
%{_datadir}/metainfo/org.freedesktop.FleetCommander.admin.metainfo.xml

%files -n fleet-commander-logger
%attr(755, root, root) %{_libexecdir}/fleet-commander-logger
%attr(755, root, root) %{_libexecdir}/firefox-bookmark-fclogger
%dir %{_datadir}/fleet-commander-logger
%attr(644, -, -) %{_datadir}/fleet-commander-logger/python/*.py
%exclude %{_datadir}/fleet-commander-logger/python/*.py[co]
%exclude %{_datadir}/fleet-commander-logger/python/__pycache__
%{_datadir}/fleet-commander-logger/fc-chromium-policies.json
%{_sysconfdir}/xdg/autostart/fleet-commander-logger.desktop
%{_udevrulesdir}/81-fleet-commander-logger.rules
# Firefox extension files
%{_libdir}/mozilla/native-messaging-hosts/firefox_bookmark_fclogger.json
%{_datadir}/mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}/{c73e87a7-b5a1-4b6f-b10b-0bd70241a64d}.xpi

%changelog
* Wed May 19 2021 Oliver Gutierrez <ogutierrez@redhat.com> - 0.16.0-1
- Deprecation of Python2

* Mon Jul 27 2020 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Wed Mar 25 2020 Oliver Gutierrez <ogutierrez@redhat.com> - 0.15.1-1
- Updated to version 0.15.1

* Tue Jan 28 2020 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Mon Dec 23 2019 Oliver Gutierrez <ogutierrez@redhat.com> - 0.15.0-1
- Added firefox bookmarks support
- Updated to version 0.15.0

* Mon Sep 16 2019 Oliver Gutierrez <ogutierrez@redhat.com> - 0.14.1-1
- Updated to version 0.14.1

* Thu Jul 25 2019 Fedora Release Engineering <releng@fedoraproject.org> - 0.14.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Wed Feb 27 2019 Oliver Gutierrez <ogutierrez@redhat.com> - 0.14.0-2
- Updated specfile with changelog

* Wed Feb 27 2019 Oliver Gutierrez <ogutierrez@redhat.com> - 0.14.0-1
- Updated to version 0.14.0-1

* Thu Jan 31 2019 Fedora Release Engineering <releng@fedoraproject.org> - 0.12.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Fri Sep 7 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.12.1-1
- Updated specfile for Python2 (EPEL) and Python3 (any other system)
- Updated to version 0.12.1-1

* Wed Aug 1 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.10-2
- Moved udev rules file to udevrulesdir

* Tue Jul 31 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.10-1
- Downgraded requirements for fleet commander logger to use python2

* Thu Jul 12 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.9-1
- Fixed errors in Chromium policy file access
- Fixed unhandled exception accessing non existent virtio device file

* Mon Jul 02 2018 Miro Hrončok <mhroncok@redhat.com> - 0.10.8-6
- Rebuilt for Python 3.7

* Tue Jun 19 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.8-5
- Removed Python 3 dependency from admin package

* Tue Jun 19 2018 Miro Hrončok <mhroncok@redhat.com> - 0.10.8-4
- Rebuilt for Python 3.7

* Fri Jun 15 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.8-3
- Fixed python3 dependency for EPEL7

* Thu Jun 14 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.8-2
- Fixed dependency for EPEL7

* Thu Jun 7 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.8-1
- Updated to release 0.10.8
- Migrated logger to python3

* Wed Apr 11 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.7-1
- Updated to release 0.10.7

* Fri Mar 30 2018 Iryna Shcherbina <ishcherb@redhat.com> - 0.10.6-4
- Fixed EPEL conditionals for Fedora builds

* Fri Mar 23 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.6-3
- Fixed EPEL specfile conditionals

* Tue Mar 20 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.6-2
- Fixed dependencies

* Tue Mar 20 2018 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.6-1
- Added support for Chromium/Chrome settings and bookmarks
- Added support for Firefox settings
- Bundled our own bootstrap and jquery due to cockpit removing them from plugins
- Updated package for 0.10.6 release

* Thu Mar 01 2018 Iryna Shcherbina <ishcherb@redhat.com> - 0.10.5-3
- Update Python 2 dependency declarations to new packaging standards
  (See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3)

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 0.10.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Nov 21 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.5-1
- Updated package for 0.10.5 release

* Fri Nov 3 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.4-1
- Added appstream metadata information

* Thu Oct 19 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.3-2
- Fixed missing dependencies on python2-ipalib and python2-ipaclient

* Wed Sep 13 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.3-1
- Added hostcategory feature
- Updated package for 0.10.3 release

* Mon Jul 17 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.2-1
- Updated package for 0.10.2 release

* Sat Jul 15 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.1-1
- Updated package for 0.10.1 release

* Mon Jul 10 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.10.0-1
- Updated package for 0.10.0 release

* Mon Jul 10 2017 Oliver Gutierrez <ogutierrez@redhat.com> - 0.9.1-1
- Updated package for 0.9.1 release

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
