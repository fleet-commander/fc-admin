fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA     = fleet-commander-logger.desktop

fleet_commander_admin_configdir = ${sysconfdir}/xdg/
fleet_commander_admin_config_in_files = fleet-commander-admin.conf.in
fleet_commander_admin_config_DATA = fleet-commander-admin.conf

fleet_commander_dbus_servicedir = ${datarootdir}/dbus-1/services/
fleet_commander_dbus_service_in_files = org.freedesktop.FleetCommander.service.in
fleet_commander_dbus_service_DATA = org.freedesktop.FleetCommander.service

fleet_commander_goa_providersdir = ${fcadmindir}
fleet_commander_goa_providers_DATA = fc-goa-providers.ini

fleet_commander_udev_rulesdir = ${sysconfdir}/udev/rules.d/
fleet_commander_udev_rules_DATA = 81-fleet-commander-logger.rules

fleet_commander_dbus_shellwrapperdir = ${libexecdir}
fleet_commander_dbus_shellwrapper_in_files = fleet-commander-admin.in
fleet_commander_dbus_shellwrapper_DATA = fleet-commander-admin

EXTRA_DIST = \
	$(fleet_commander_logger_desktop_in_files)     \
	$(fleet_commander_admin_config_in_files)       \
	$(fleet_commander_dbus_service_in_files)       \
	$(fleet_commander_goa_providers_DATA)          \
	$(fleet_commander_udev_rules_DATA)             \
	$(fleet_commander_dbus_shellwrapper_in_files)

CLEANFILES = \
	$(fleet_commander_logger_desktop_DATA)      \
	$(fleet_commander_admin_config_DATA)
