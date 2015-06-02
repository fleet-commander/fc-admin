fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA = $(fleet_commander_logger_desktop_in_files:.desktop.in=.desktop)

fleet_commander_admin_configdir = ${sysconfdir}/xdg/
fleet_commander_admin_config_in_files = fleet-commander-admin.conf.in
fleet_commander_admin_config_DATA = $(fleet_commander_admin_config_in_files:.conf.in=.conf)

fleet_commander_logger_configdir = ${sysconfdir}/xdg/
fleet_commander_logger_config_DATA = fleet-commander-logger.conf

fleet_commander_controller_configdir = ${sysconfdir}/xdg/
fleet_commander_controller_config_DATA = fleet-commander-controller.conf

fleet_commander_vnc_session_servicedir = $(systemdsystemunitdir)
fleet_commander_vnc_session_service_in_files = fleet-commander-vnc-session.service.in
fleet_commander_vnc_session_service_DATA = fleet-commander-vnc-session.service

fleet_commander_controller_servicedir = $(systemdsystemunitdir)
fleet_commander_controller_service_in_files = fleet-commander-controller.service.in
fleet_commander_controller_service_DATA = fleet-commander-controller.service

fleet_commander_admin_servicedir = $(systemdsystemunitdir)
fleet_commander_admin_service_in_files = fleet-commander-admin.service.in
fleet_commander_admin_service_DATA = fleet-commander-admin.service

EXTRA_DIST = \
	$(fleet_commander_logger_desktop_in_files)     \
	$(fleet_commander_admin_config_in_files)       \
	$(fleet_commander_service_in_files)            \
	$(fleet_commander_controller_service_in_files) \
	$(fleet_commander_logger_config_DATA)          \
	$(fleet_commander_controller_config_DATA)

CLEANFILES = \
	$(fleet_commander_logger_desktop_DATA)      \
	$(fleet_commander_vnc_session_service_DATA) \
	$(fleet_commander_admin_service_DATA)       \
	$(fleet_commander_controller_service_DATA)
