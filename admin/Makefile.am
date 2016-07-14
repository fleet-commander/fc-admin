fc_admin_pydir = ${fcpythondir}/fleetcommander
fc_admin_py_SCRIPTS = \
	fleetcommander/__init__.py   \
	fleetcommander/collectors.py \
	fleetcommander/database.py \
	fleetcommander/fcdbus.py            \
	fleetcommander/flaskless.py \
	fleetcommander/libvirtcontroller.py \
	fleetcommander/sshcontroller.py \
	fleetcommander/utils.py

fc_admin_constsdir = ${fcpythondir}/fleetcommander
fc_admin_consts_in_files = fleetcommander/constants.py.in
fc_admin_consts_DATA = fleetcommander/constants.py

fc_jsdir   = ${fcadmindir}/cockpit/js
fc_js_DATA = \
	cockpit/js/base.js \
	cockpit/js/fcdbusclient.js \
	cockpit/js/fcspiceclient.js \
	cockpit/js/index.js \
	cockpit/js/livesession.js \
	cockpit/js/spice_debug_bypass.js

fc_spicehtml5dir = ${fcadmindir}/cockpit/js/spice-html5
fc_spicehtml5_DATA = \
	cockpit/js/spice-html5/cursor.js \
	cockpit/js/spice-html5/bitmap.js \
	cockpit/js/spice-html5/playback.js \
	cockpit/js/spice-html5/spiceconn.js \
	cockpit/js/spice-html5/ticket.js \
	cockpit/js/spice-html5/filexfer.js \
	cockpit/js/spice-html5/quic.js \
	cockpit/js/spice-html5/thirdparty/prng4.js \
	cockpit/js/spice-html5/thirdparty/rsa.js \
	cockpit/js/spice-html5/thirdparty/sha1.js \
	cockpit/js/spice-html5/thirdparty/rng.js \
	cockpit/js/spice-html5/thirdparty/jsbn.js \
	cockpit/js/spice-html5/main.js \
	cockpit/js/spice-html5/webm.js \
	cockpit/js/spice-html5/spicetype.js \
	cockpit/js/spice-html5/simulatecursor.js \
	cockpit/js/spice-html5/enums.js \
	cockpit/js/spice-html5/inputs.js \
	cockpit/js/spice-html5/atKeynames.js \
	cockpit/js/spice-html5/display.js \
	cockpit/js/spice-html5/png.js \
	cockpit/js/spice-html5/spicearraybuffer.js \
	cockpit/js/spice-html5/resize.js \
	cockpit/js/spice-html5/spicemsg.js \
	cockpit/js/spice-html5/wire.js \
	cockpit/js/spice-html5/lz.js \
	cockpit/js/spice-html5/utils.js \
	cockpit/js/spice-html5/spicedataview.js

fc_spicehtml5thirdpartydir = ${fcadmindir}/cockpit/js/spice-html5/thirdparty
fc_spicehtml5thirdparty_DATA = \
	cockpit/js/spice-html5/thirdparty/prng4.js \
	cockpit/js/spice-html5/thirdparty/rsa.js \
	cockpit/js/spice-html5/thirdparty/sha1.js \
	cockpit/js/spice-html5/thirdparty/rng.js \
	cockpit/js/spice-html5/thirdparty/jsbn.js

fc_cockpitdir = ${fcadmindir}/cockpit
fc_cockpit_DATA = \
	cockpit/index.html \
	cockpit/livesession.html \
	cockpit/manifest.json

fc_cssdir = ${fcadmindir}/cockpit/css
fc_css_DATA = \
	cockpit/css/main.css

EXTRA_DIST = \
	     $(fc_admin_py_SCRIPTS) \
	     $(fc_js_DATA) \
	     $(fc_spicehtml5_DATA) \
	     $(fc_spicehtml5thirdparty_DATA) \
	     $(fc_cockpit_DATA) \
	     $(fc_css_DATA)                  \
	     $(fc_admin_consts_in_files)

CLEANFILESM = \
	$(fc_admin_consts_DATA)
