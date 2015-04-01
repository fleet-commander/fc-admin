AC_INIT(fleet-commander-admin, 0.1, aruiz@redhat.com)
AC_COPYRIGHT([Copyright 2014,2015 Red Hat, Inc.])

AC_PREREQ(2.64)
AM_INIT_AUTOMAKE([dist-xz])
AM_MAINTAINER_MODE
AC_CONFIG_MACRO_DIR([m4])
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])



AC_PATH_PROG([XVNC],[Xvnc])
AC_PATH_PROG([XRANDR], [xrandr])
AC_PATH_PROG([GNOME_SESSION], [gnome-session])
if test x$XVNC = x ; then
  AC_MSG_ERROR([Could not find Xvnc])
fi
if test x$XRANDR = x ; then
  AC_MSG_ERROR([Could not find xrandr])
fi
if test x$GNOME_SESSION = x ; then
  AC_MSG_ERROR([Could not find gnome-session])
fi


PKG_PROG_PKG_CONFIG
AC_ARG_WITH([systemdsystemunitdir],
     [AS_HELP_STRING([--with-systemdsystemunitdir=DIR], [Directory for systemd service files])],,
     [with_systemdsystemunitdir=auto])
AS_IF([test "x$with_systemdsystemunitdir" = "xyes" -o "x$with_systemdsystemunitdir" = "xauto"], [
     def_systemdsystemunitdir=$($PKG_CONFIG --variable=systemdsystemunitdir systemd)

     AS_IF([test "x$def_systemdsystemunitdir" = "x"],
   [AS_IF([test "x$with_systemdsystemunitdir" = "xyes"],
    [AC_MSG_ERROR([systemd support requested but pkg-config unable to query systemd package])])
    with_systemdsystemunitdir=no],
   [with_systemdsystemunitdir="$def_systemdsystemunitdir"])])
AS_IF([test "x$with_systemdsystemunitdir" != "xno"],
      [AC_SUBST([systemdsystemunitdir], [$with_systemdsystemunitdir])])
AM_CONDITIONAL([HAVE_SYSTEMD], [test "x$with_systemdsystemunitdir" != "xno"])

if test "x$with_systemdsystemunitdir" = "xno"; then
  AC_MSG_ERROR([systemd support is mandatory])
fi

################
# Dependencies #
################

# TODO: python3, python3-gobject, json-glib

AM_PATH_PYTHON(3.0,, [:])
AC_PYTHON_MODULE([gi], [mandatory])

# libexecdir expansion for .desktop file
# TODO: Make xdgconfigdir parametric
privlibexecdir='${libexecdir}'
xdgconfigdir='${sysconfdir}'/xdg
profilesdir='${localstatedir}'/fleet-commander-admin
AC_SUBST(privlibexecdir)
AC_SUBST(xdgconfigdir)
AC_SUBST(profilesdir)

AC_SUBST(XVNC)
AC_SUBST(XRANDR)
AC_SUBST(GNOME_SESSION)

AS_AC_EXPAND(XDGCONFIGDIR, "$xdgconfigdir")
AS_AC_EXPAND(PRIVLIBEXECDIR, "$privlibexecdir")
AS_AC_EXPAND(PROFILESDIR, "$profilesdir")

AS_AC_EXPAND(XVNC,"$XVNC")
AS_AC_EXPAND(XRANDR,"$XRANDR")
AS_AC_EXPAND(GNOME_SESSION,"$GNOME_SESSION")

AC_SUBST(SYSTEMUNITDIR)

AC_OUTPUT([
Makefile
data/fleet-commander-logger.desktop
data/fleet-commander-admin.conf
data/fleet-commander-vnc-session.service
data/Makefile
tools/Makefile
])
