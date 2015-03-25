fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA = $(fleet_commander_logger_desktop_in_files:.desktop.in=.desktop)

fleet_commander_logger_configdir = ${sysconfdir}/xdg/
fleet_commander_logger_config_DATA = fleet-commander-logger.conf

EXTRA_DIST = \
	$(fleet_commander_logger_config_DATA) \
	$(fleet_commander_logger_desktop_in_files)

CLEANFILES = $(fleet_commander_logger_desktop_DATA)
