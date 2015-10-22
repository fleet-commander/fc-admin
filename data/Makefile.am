fleet_commander_logger_desktopdir = ${sysconfdir}/xdg/autostart
fleet_commander_logger_desktop_in_files = fleet-commander-logger.desktop.in
fleet_commander_logger_desktop_DATA     = fleet-commander-logger.desktop

gnome_software_service_desktopdir   = ${sysconfdir}/xdg/autostart
gnome_software_service_desktop_DATA = gnome-software-service.desktop

fleet_commander_admin_configdir = ${sysconfdir}/xdg/
fleet_commander_admin_config_in_files = fleet-commander-admin.conf.in
fleet_commander_admin_config_DATA = fleet-commander-admin.conf

fleet_commander_vnc_resolutiondir = ${sysconfdir}/xdg/
fleet_commander_vnc_resolution_DATA = monitors.xml

gnome_initial_setup_donedir = ${sysconfdir}/xdg/
gnome_initial_setup_done_DATA = gnome-initial-setup-done

fleet_commander_logger_configdir = ${sysconfdir}/xdg/
fleet_commander_logger_config_DATA = fleet-commander-logger.conf

fleet_commander_controller_configdir = ${sysconfdir}/xdg/
fleet_commander_controller_config_in_files = fleet-commander-controller.conf.in
fleet_commander_controller_config_DATA     = fleet-commander-controller.conf

fleet_commander_vnc_session_servicedir = $(systemdsystemunitdir)
fleet_commander_vnc_session_service_in_files = fleet-commander-vnc-session.service.in
fleet_commander_vnc_session_service_DATA = fleet-commander-vnc-session.service

fleet_commander_controller_servicedir = $(systemdsystemunitdir)
fleet_commander_controller_service_in_files = fleet-commander-controller.service.in
fleet_commander_controller_service_DATA = fleet-commander-controller.service

fleet_commander_admin_servicedir = $(systemdsystemunitdir)
fleet_commander_admin_service_in_files = fleet-commander-admin.service.in
fleet_commander_admin_service_DATA = fleet-commander-admin.service

fleet_commander_apache_configdir = ${sysconfdir}/httpd/conf.d/
fleet_commander_apache_config_in_files = fleet-commander-apache.conf.in
fleet_commander_apache_config_DATA     = fleet-commander-apache.conf

EXTRA_DIST = \
    $(gnome_software_service_desktop_DATA)         \
	$(fleet_commander_logger_desktop_in_files)     \
	$(fleet_commander_admin_config_in_files)       \
	$(fleet_commander_vnc_resolution_DATA)         \
	$(gnome_initial_setup_done_DATA)               \
	$(fleet_commander_service_in_files)            \
	$(fleet_commander_controller_service_in_files) \
	$(fleet_commander_logger_config_DATA)          \
	$(fleet_commander_controller_config_DATA)	   \
	$(fleet_commander_apache_service_in_files) 	   \
	$(fleet_commander_apache_config_DATA)

CLEANFILES = \
	$(fleet_commander_logger_desktop_DATA)      \
	$(fleet_commander_admin_config_DATA)        \
	$(fleet_commander_controller_config_DATA)   \
	$(fleet_commander_vnc_session_service_DATA) \
	$(fleet_commander_controller_service_DATA)  \
	$(fleet_commander_admin_service_DATA)

