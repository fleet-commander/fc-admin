fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA     = fleet-commander-logger.desktop

fleet_commander_admin_configdir = ${sysconfdir}/xdg/
fleet_commander_admin_config_in_files = fleet-commander-admin.conf.in
fleet_commander_admin_config_DATA = fleet-commander-admin.conf

fleet_commander_apache_configdir = ${sysconfdir}/xdg/
fleet_commander_apache_config_in_files = fleet-commander-apache.conf.in
fleet_commander_apache_config_DATA     = fleet-commander-apache.conf

#fleet_commander_libreoffice_dconfdir = ${fchomedir}/.config/libreoffice
#fleet_commander_libreoffice_dconf_DATA   = dconfwrite

fleet_commander_dbus_servicedir = ${datarootdir}/dbus-1/system-services/
fleet_commander_dbus_service_in_files = org.freedesktop.FleetCommander.service.in
fleet_commander_dbus_service_DATA = org.freedesktop.FleetCommander.service

fleet_commander_dbus_systemd_servicedir = $(systemdsystemunitdir)
fleet_commander_dbus_systemd_service_in_files = fleet-commander-dbus.service.in
fleet_commander_dbus_systemd_service_DATA = fleet-commander-dbus.service

fleet_commander_dbus_configdir = ${sysconfdir}/dbus-1/system.d/
fleet_commander_dbus_config_DATA = org.freedesktop.FleetCommander.conf

fleet_commander_admin_commanddir = ${prefix}/bin/
fleet_commander_admin_command_in_files = fc-admin-standalone.in
fleet_commander_admin_command_DATA = fc-admin-standalone

EXTRA_DIST = \
    $(gnome_software_service_desktop_DATA)         \
	$(fleet_commander_logger_desktop_in_files)     \
	$(fleet_commander_admin_config_in_files)       \
	$(fleet_commander_admin_service_in_files)      \
	$(fleet_commander_apache_service_in_files)     \
	$(fleet_commander_apache_config_DATA)          \
	$(fleet_commander_dbus_service_in_files)       \
	$(fleet_commander_dbus_config_DATA)            \
	$(fleet_commander_admin_command_in_files)      \
	$(fleet_commander_dbus_systemd_service_in_files)

CLEANFILES = \
	$(fleet_commander_logger_desktop_DATA)      \
	$(fleet_commander_admin_config_DATA)        \
	$(fleet_commander_admin_service_DATA)       \
	$(fleet_commander_dbus_service_DATA)        \
	$(fleet_commander_admin_command_DATA)       \
	$(fleet_commander_dbus_systemd_service_DATA)

