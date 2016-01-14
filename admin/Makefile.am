fc_admin_pydir = ${fcpythondir}/fleetcommander
fc_admin_py_SCRIPTS = \
	fleetcommander/__init__.py   \
	fleetcommander/admin.py      \
	fleetcommander/collectors.py \
	fleetcommander/database.py \
	fleetcommander/fcdbus.py            \
	fleetcommander/flaskless.py \
	fleetcommander/libvirtcontroller.py \
	fleetcommander/utils.py

fc_admin_constsdir = ${fcpythondir}/fleetcommander
fc_admin_consts_in_files = fleetcommander/constants.py.in
fc_admin_consts_DATA = fleetcommander/constants.py

fc_admin_wsgidir = ${libexecdir}
fc_admin_wsgi_SCRIPTS = \
	admin.wsgi

fc_jsdir   = ${fcdatadir}/js
fc_js_DATA = \
		$(wildcard js/*.js)

fc_spicehtml5dir = ${fcdatadir}/js/spice-html5
fc_spicehtml5_DATA = \
	js/spice-html5/cursor.js \
	js/spice-html5/bitmap.js \
	js/spice-html5/playback.js \
	js/spice-html5/spiceconn.js \
	js/spice-html5/ticket.js \
	js/spice-html5/filexfer.js \
	js/spice-html5/quic.js \
	js/spice-html5/thirdparty/prng4.js \
	js/spice-html5/thirdparty/rsa.js \
	js/spice-html5/thirdparty/sha1.js \
	js/spice-html5/thirdparty/rng.js \
	js/spice-html5/thirdparty/jsbn.js \
	js/spice-html5/main.js \
	js/spice-html5/webm.js \
	js/spice-html5/spicetype.js \
	js/spice-html5/simulatecursor.js \
	js/spice-html5/enums.js \
	js/spice-html5/inputs.js \
	js/spice-html5/atKeynames.js \
	js/spice-html5/display.js \
	js/spice-html5/png.js \
	js/spice-html5/spicearraybuffer.js \
	js/spice-html5/resize.js \
	js/spice-html5/spicemsg.js \
	js/spice-html5/wire.js \
	js/spice-html5/lz.js \
	js/spice-html5/utils.js \
	js/spice-html5/spicedataview.js

fc_spicehtml5thirdpartydir = ${fcdatadir}/js/spice-html5/thirdparty
fc_spicehtml5thirdparty_DATA = \
	js/spice-html5/thirdparty/prng4.js \
	js/spice-html5/thirdparty/rsa.js \
	js/spice-html5/thirdparty/sha1.js \
	js/spice-html5/thirdparty/rng.js \
	js/spice-html5/thirdparty/jsbn.js

fc_fontdir = ${fcdatadir}/fonts
fc_font_DATA = \
	$(wildcard fonts/*.ttf) \
	$(wildcard fonts/*.eot) \
	$(wildcard fonts/*.svg) \
	$(wildcard fonts/*.woff) \
	$(wildcard fonts/*.woff2)

fc_imgdir = ${fcdatadir}/img
fc_img_DATA = \
	      $(wildcard img/*.png) \
	      $(wildcard img/*.img) \
     	      $(wildcard img/*.gif) \
      	      $(wildcard img/*.ico) \
     	      $(wildcard img/*.svg)

fc_tmpldir = ${fcdatadir}/templates
fc_tmpl_DATA = $(wildcard templates/*.html)

fc_cssdir = ${fcdatadir}/css
fc_css_DATA = $(wildcard css/*.css)

EXTRA_DIST = \
	     $(fc_admin_py_SCRIPTS) \
	     $(fc_admin_wsgi_SCRIPTS) \
	     $(fc_js_DATA) \
	     $(fc_spicehtml5_DATA) \
	     $(fc_spicehtml5thirdparty_DATA) \
	     $(fc_img_DATA) \
	     $(fc_tmpl_DATA) \
	     $(fc_css_DATA)                  \
	     $(fc_font_DATA)                 \
	     $(fc_admin_consts_in_files)

CLEANFILESM = \
	$(fc_admin_consts_DATA)
