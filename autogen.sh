#!/bin/sh
git submodule update --init --recursive
aclocal \
&& automake --gnu -a -c \
&& autoconf
./configure $@
