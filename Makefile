gsettings-logger: gsettings-logger.c
	gcc -g `pkg-config --libs --cflags json-glib-1.0 gio-2.0`  gsettings-logger.c -o gsettings-logger
