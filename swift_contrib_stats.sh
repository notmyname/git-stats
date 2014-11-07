#!/bin/bash

ORIGPWD=`pwd`
SWIFTDIR="$HOME/Documents/swift"

mv ${ORIGPWD}/swift_contrib_stats.data ${SWIFTDIR}/contrib_stats.data 2>/dev/null

cd ${SWIFTDIR}
python "$ORIGPWD"/contrib_stats.py
mv ${SWIFTDIR}/active_contribs.png ${ORIGPWD}/swift_active_contribs.png
mv ${SWIFTDIR}/contrib_stats.data ${ORIGPWD}/swift_contrib_stats.data
cd ${ORIGPWD}
