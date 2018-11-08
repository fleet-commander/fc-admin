fc_admin_pydir = ${fcpythondir}/fleetcommander
fc_admin_py_SCRIPTS = \
	fleetcommander/__init__.py \
	fleetcommander/mergers.py \
	fleetcommander/database.py \
	fleetcommander/fcdbus.py \
	fleetcommander/fcfreeipa.py \
	fleetcommander/fcad.py \
	fleetcommander/goa.py \
	fleetcommander/libvirtcontroller.py \
	fleetcommander/sshcontroller.py \
	fleetcommander/utils.py

fc_admin_constsdir = ${fcpythondir}/fleetcommander
fc_admin_consts_in_files = fleetcommander/constants.py.in
fc_admin_consts_DATA = fleetcommander/constants.py

fc_jsdir   = ${datarootdir}/cockpit/fleet-commander-admin/js
fc_js_DATA = \
	cockpit/fleet-commander-admin/js/jquery-3.3.1.min.js \
	cockpit/fleet-commander-admin/js/bootstrap-4.0.0.min.js \
	cockpit/fleet-commander-admin/js/base.js \
	cockpit/fleet-commander-admin/js/fcdbusclient.js \
	cockpit/fleet-commander-admin/js/fcspiceclient.js \
	cockpit/fleet-commander-admin/js/collectors.js \
	cockpit/fleet-commander-admin/js/index.js \
	cockpit/fleet-commander-admin/js/highlightedapps.js \
	cockpit/fleet-commander-admin/js/goa.js \
	cockpit/fleet-commander-admin/js/livesession.js \
	cockpit/fleet-commander-admin/js/spice_debug_bypass.js

fc_goaimgdir   = ${datarootdir}/cockpit/fleet-commander-admin/img/goa
fc_goaimg_DATA = \
	cockpit/fleet-commander-admin/img/goa/exchange.png \
	cockpit/fleet-commander-admin/img/goa/facebook.png \
	cockpit/fleet-commander-admin/img/goa/flickr.png \
	cockpit/fleet-commander-admin/img/goa/foursquare.png \
	cockpit/fleet-commander-admin/img/goa/google.png \
	cockpit/fleet-commander-admin/img/goa/imap_smtp.png \
	cockpit/fleet-commander-admin/img/goa/kerberos.png \
	cockpit/fleet-commander-admin/img/goa/lastfm.png \
	cockpit/fleet-commander-admin/img/goa/owncloud.png \
	cockpit/fleet-commander-admin/img/goa/pocket.png \
	cockpit/fleet-commander-admin/img/goa/windows_live.png

fc_goatelepathyimgdir   = ${datarootdir}/cockpit/fleet-commander-admin/img/goa/telepathy
fc_goatelepathyimg_DATA = \
	cockpit/fleet-commander-admin/img/goa/telepathy/jabber.png

fc_spicehtml5dir = ${datarootdir}/cockpit/fleet-commander-admin/js/spice-html5
fc_spicehtml5_DATA = \
	cockpit/fleet-commander-admin/js/spice-html5/cursor.js \
	cockpit/fleet-commander-admin/js/spice-html5/bitmap.js \
	cockpit/fleet-commander-admin/js/spice-html5/playback.js \
	cockpit/fleet-commander-admin/js/spice-html5/spiceconn.js \
	cockpit/fleet-commander-admin/js/spice-html5/ticket.js \
	cockpit/fleet-commander-admin/js/spice-html5/filexfer.js \
	cockpit/fleet-commander-admin/js/spice-html5/quic.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/prng4.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/rsa.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/sha1.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/rng.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/jsbn.js \
	cockpit/fleet-commander-admin/js/spice-html5/main.js \
	cockpit/fleet-commander-admin/js/spice-html5/webm.js \
	cockpit/fleet-commander-admin/js/spice-html5/spicetype.js \
	cockpit/fleet-commander-admin/js/spice-html5/simulatecursor.js \
	cockpit/fleet-commander-admin/js/spice-html5/enums.js \
	cockpit/fleet-commander-admin/js/spice-html5/inputs.js \
	cockpit/fleet-commander-admin/js/spice-html5/port.js \
	cockpit/fleet-commander-admin/js/spice-html5/atKeynames.js \
	cockpit/fleet-commander-admin/js/spice-html5/display.js \
	cockpit/fleet-commander-admin/js/spice-html5/png.js \
	cockpit/fleet-commander-admin/js/spice-html5/spicearraybuffer.js \
	cockpit/fleet-commander-admin/js/spice-html5/resize.js \
	cockpit/fleet-commander-admin/js/spice-html5/spicemsg.js \
	cockpit/fleet-commander-admin/js/spice-html5/wire.js \
	cockpit/fleet-commander-admin/js/spice-html5/lz.js \
	cockpit/fleet-commander-admin/js/spice-html5/utils.js \
	cockpit/fleet-commander-admin/js/spice-html5/spicedataview.js

fc_spicehtml5thirdpartydir = ${datarootdir}/cockpit/fleet-commander-admin/js/spice-html5/thirdparty
fc_spicehtml5thirdparty_DATA = \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/prng4.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/rsa.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/sha1.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/rng.js \
	cockpit/fleet-commander-admin/js/spice-html5/thirdparty/jsbn.js

fc_cockpitdir = ${datarootdir}/cockpit/fleet-commander-admin
fc_cockpit_DATA = \
	cockpit/fleet-commander-admin/index.html \
	cockpit/fleet-commander-admin/livesession.html \
	cockpit/fleet-commander-admin/manifest.json

fc_cssdir = ${datarootdir}/cockpit/fleet-commander-admin/css
fc_css_DATA = \
	cockpit/fleet-commander-admin/css/bootstrap-4.0.0.min.css \
	cockpit/fleet-commander-admin/css/main.css

EXTRA_DIST = \
	     $(fc_admin_py_SCRIPTS) \
	     $(fc_js_DATA) \
	     $(fc_spicehtml5_DATA) \
	     $(fc_spicehtml5thirdparty_DATA) \
	     $(fc_cockpit_DATA) \
	     $(fc_css_DATA) \
			 $(fc_goaimg_DATA) \
			 $(fc_goatelepathyimg_DATA) \
	     $(fc_admin_consts_in_files)

CLEANFILESM = \
	$(fc_admin_consts_DATA)
