#!/bin/sh
aclocal \
&& automake --gnu -a -c \
&& autoconf
