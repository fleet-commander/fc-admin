fc-gsettings-logger: fc-gsettings-logger.c
	gcc -g `pkg-config --libs --cflags libsoup-2.4 json-glib-1.0 gio-2.0`  fc-gsettings-logger.c -o fc-gsettings-logger
install: fc-gsettings-logger
	cp fc-gsettings-logger ~/.local/bin
	cp data/fc-gsettings-logger.desktop ~/.config/autostart

