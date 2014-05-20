fc-gsettings-logger: fc-gsettings-logger.c
	gcc -g `pkg-config --libs --cflags libsoup-2.4 json-glib-1.0 gio-2.0`  fc-gsettings-logger.c -o fc-gsettings-logger
install: fc-gsettings-logger
	mkdir -p /home/fc-user/.local/bin
	mkdir -p /home/fc-user/.config/autostart
	chown fc-user -R /home/fc-user/.local
	chown fc-user -R /home/fc-user/.config
	cp fc-gsettings-logger /home/fc-user/.local/bin
	cp data/fc-gsettings-logger.desktop /home/fc-user/.config/autostart

