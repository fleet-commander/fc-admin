AC_INIT(fleet-commander-admin, 0.10.3, aruiz@redhat.com)
AC_COPYRIGHT([Copyright 2014,2015,2016,2017 Red Hat, Inc.])

AC_PREREQ(2.64)
AM_INIT_AUTOMAKE([no-dist-gzip dist-xz])
AM_MAINTAINER_MODE
AC_CONFIG_MACRO_DIR([m4])
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])

AC_PATH_PROG([RUNUSER], [runuser])
#AC_PATH_PROG([SSH], [ssh])
#AC_PATH_PROG([SSHKEYGEN], [ssh-keygen])
#AC_PATH_PROG([SSHKEYSCAN], [ssh-keyscan])
AC_PATH_PROG([MKDIR], [mkdir])

if test x$RUNUSER = x ; then
  AC_MSG_ERROR([Could not find runuser])
fi
#if test x$SSH = x ; then
#  AC_MSG_ERROR([Could not find ssh])
#fi
#if test x$SSHKEYGEN = x ; then
#  AC_MSG_ERROR([Could not find ssh-keygen])
#fi
#if test x$SSHKEYSCAN = x ; then
#  AC_MSG_ERROR([Could not find ssh-keyscan])
#fi

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

AM_PATH_PYTHON([2],, [:])
AC_PYTHON_MODULE([pexpect], [mandatory])
AC_PYTHON_MODULE([dbus], [mandatory])
AC_PYTHON_MODULE([gobject], [mandatory])
AC_PYTHON_MODULE([gi], [mandatory])
AC_PYTHON_MODULE([libvirt], [mandatory])
AC_PYTHON_MODULE([dbusmock])

# libexecdir expansion for .desktop file
# TODO: Make xdgconfigdir parametric
privlibexecdir='${libexecdir}'
xdgconfigdir='${sysconfdir}'/xdg
adminstatedir='${localstatedir}'/lib/fleet-commander-admin
profilesdir='${localstatedir}'/lib/fleet-commander-admin/profiles
databasefile='${localstatedir}'/lib/fleet-commander-admin/database.db
fchomedir='${localstatedir}'/lib/fleet-commander
fcadmindir='${datarootdir}'/fleet-commander-admin
fcpythondir='${datarootdir}'/fleet-commander-admin/python
fcconfigfile='${sysconfdir}'/xdg/fleet-commander-admin.conf
cockpitdir='${datarootdir}'/cockpit

AC_SUBST(privlibexecdir)
AC_SUBST(xdgconfigdir)
AC_SUBST(adminstatedir)
AC_SUBST(profilesdir)
AC_SUBST(databasefile)
AC_SUBST(fchomedir)
AC_SUBST(fcadmindir)
AC_SUBST(cockpitdir)
AC_SUBST(fcpythondir)
AC_SUBST(fcconfigfile)

AS_AC_EXPAND(XDGCONFIGDIR, "$xdgconfigdir")
AS_AC_EXPAND(PRIVLIBEXECDIR, "$privlibexecdir")
AS_AC_EXPAND(ADMINSTATEDIR, "$adminstatedir")
AS_AC_EXPAND(PROFILESDIR, "$profilesdir")
AS_AC_EXPAND(DATABASEFILE, "$databasefile")
AS_AC_EXPAND(FCHOMEDIR, "$fchomedir")
AS_AC_EXPAND(FCADMINDIR, "$fcadmindir")
AS_AC_EXPAND(COCKPITDIR, "$cockpitdir")
AS_AC_EXPAND(FCPYTHONDIR, "$fcpythondir")
AS_AC_EXPAND(FCCONFIGFILE, "$fcconfigfile")

AC_SUBST(SYSTEMUNITDIR)

AC_OUTPUT([
Makefile
data/Makefile
logger/Makefile
tests/Makefile
admin/Makefile
admin/fleetcommander/constants.py
data/fleet-commander-logger.desktop
data/fleet-commander-admin.conf
data/org.freedesktop.FleetCommander.service
data/fleet-commander-admin
])
