#!/bin/bash

ORIGPWD=`pwd`
SWIFTDIR="$HOME/Documents/swift"

mv ${ORIGPWD}/contrib_stats.data ${SWIFTDIR}/contrib_stats.data 2>/dev/null

cd ${SWIFTDIR}
python "$ORIGPWD"/contrib_stats.py $@
mv ${SWIFTDIR}/active_contribs.png ${ORIGPWD}/active_contribs.png
mv ${SWIFTDIR}/total_contribs.png ${ORIGPWD}/total_contribs.png
mv ${SWIFTDIR}/contrib_deltas.png ${ORIGPWD}/contrib_deltas.png
mv ${SWIFTDIR}/contrib_activity.png ${ORIGPWD}/contrib_activity.png
mv ${SWIFTDIR}/contrib_stats.data ${ORIGPWD}/contrib_stats.data
cd ${ORIGPWD}
