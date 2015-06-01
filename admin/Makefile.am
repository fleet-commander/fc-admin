fc_admin_pydir = ${libexecdir}
fc_admin_py_SCRIPTS = fleet-commander-admin.py

fc_jsdir   = @FCDATADIR@/js
fc_js_DATA = \
	     $(wildcard js/*.js)

fc_novncdir = @FCDATADIR@/js/noVNC/include
fc_novnc_DATA = \
		js/noVNC/include/util.js \
		js/noVNC/include/webutil.js \
		js/noVNC/include/base64.js \
		js/noVNC/include/websock.js \
		js/noVNC/include/des.js \
		js/noVNC/include/keysymdef.js \
		js/noVNC/include/keyboard.js \
		js/noVNC/include/input.js \
		js/noVNC/include/display.js \
		js/noVNC/include/jsunzip.js \
		js/noVNC/include/keysym.js \
		js/noVNC/include/rfb.js

fc_fontdir = @FCDATADIR@/fonts
fc_font_DATA = \
	$(wildcard fonts/*.ttf) \
	$(wildcard fonts/*.eot) \
	$(wildcard fonts/*.svg) \
	$(wildcard fonts/*.woff)

fc_imgdir = @FCDATADIR@/img
fc_img_DATA = \
	      $(wildcard img/*.png) \
	      $(wildcard img/*.img) \
     	      $(wildcard img/*.gif) \
      	      $(wildcard img/*.ico) \
     	      $(wildcard img/*.svg)

fc_tmpldir = @FCDATADIR@/templates
fc_tmpl_DATA = $(wildcard templates/*.html)

fc_cssdir = @FCDATADIR@/css
fc_css_DATA = $(wildcard css/*.css)

EXTRA_DIST = \
	     $(fc_admin_py_SCRIPTS) \
	     $(fc_js_DATA) \
	     $(fc_novnc_DATA) \
	     $(fc_img_DATA) \
	     $(fc_tmpl_DATA) \
	     $(fc_css_DATA)
