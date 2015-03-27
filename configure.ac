AC_INIT(fleet-commander-admin, 0.1, aruiz@redhat.com)
AC_COPYRIGHT([Copyright 2014,2015 Red Hat, Inc.])

AC_PREREQ(2.64)
AM_INIT_AUTOMAKE([dist-xz])
AM_MAINTAINER_MODE
AC_CONFIG_MACRO_DIR([m4])
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])


# libexecdir expansion for .desktop file
privlibexecdir='${libexecdir}'
xdgconfigdir='${sysconfdir}'/xdg
profilesdir='${localstatedir}'/fleet-commander-admin

AC_SUBST(privlibexecdir)
AC_SUBST(xdgconfigdir)
AC_SUBST(profilesdir)
AS_AC_EXPAND(XDGCONFIGDIR, "$xdgconfigdir")
AS_AC_EXPAND(PRIVLIBEXECDIR, "$privlibexecdir")
AS_AC_EXPAND(PROFILESDIR, "$profilesdir")

#TODO: Make xdgconfigdir parametric

################
# Dependencies #
################

# TODO: python3, python3-gobject, json-glib

AM_PATH_PYTHON(3.0,, [:])
AC_PYTHON_MODULE([gi], [mandatory])

AC_OUTPUT([
Makefile
data/fleet-commander-logger.desktop
data/fleet-commander-admin.conf
data/Makefile
tools/Makefile
])
