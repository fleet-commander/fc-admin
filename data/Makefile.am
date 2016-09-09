fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA     = fleet-commander-logger.desktop

fleet_commander_admin_configdir = ${sysconfdir}/xdg/
fleet_commander_admin_config_in_files = fleet-commander-admin.conf.in
fleet_commander_admin_config_DATA = fleet-commander-admin.conf

fleet_commander_dbus_servicedir = ${datarootdir}/dbus-1/system-services/
fleet_commander_dbus_service_in_files = org.freedesktop.FleetCommander.service.in
fleet_commander_dbus_service_DATA = org.freedesktop.FleetCommander.service

fleet_commander_admin_systemd_servicedir = $(systemdsystemunitdir)
fleet_commander_admin_systemd_service_in_files = fleet-commander-admin.service.in
fleet_commander_admin_systemd_service_DATA = fleet-commander-admin.service

fleet_commander_dbus_configdir = ${sysconfdir}/dbus-1/system.d/
fleet_commander_dbus_config_DATA = org.freedesktop.FleetCommander.conf

fleet_commander_goa_providersdir = ${fcadmindir}
fleet_commander_goa_providers_DATA = fc-goa-providers.ini

EXTRA_DIST = \
  $(gnome_software_service_desktop_DATA)         \
	$(fleet_commander_logger_desktop_in_files)     \
	$(fleet_commander_admin_config_in_files)       \
	$(fleet_commander_dbus_service_in_files)       \
	$(fleet_commander_dbus_config_DATA)            \
	$(fleet_commander_goa_providers_DATA)          \
	$(fleet_commander_admin_systemd_service_in_files)

CLEANFILES = \
	$(fleet_commander_logger_desktop_DATA)      \
	$(fleet_commander_admin_config_DATA)        \
	$(fleet_commander_dbus_service_DATA)        \
	$(fleet_commander_admin_systemd_service_DATA)

install-data-local:
	install -d ${adminstatedir}
	install -d ${profilesdir}
