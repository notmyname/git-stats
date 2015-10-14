#!/bin/bash

ORIGPWD=`pwd`
SWIFTDIR="$HOME/Documents/swift"

mv ${ORIGPWD}/contrib_stats.data ${SWIFTDIR}/contrib_stats.data 2>/dev/null
mv ${ORIGPWD}/swift_gerrit_history.patches ${SWIFTDIR}/swift_gerrit_history.patches 2>/dev/null

cd ${SWIFTDIR}
python "$ORIGPWD"/contrib_stats.py $@
mv ${SWIFTDIR}/active_contribs.png ${ORIGPWD}/active_contribs.png
mv ${SWIFTDIR}/total_contribs.png ${ORIGPWD}/total_contribs.png
mv ${SWIFTDIR}/contrib_activity.png ${ORIGPWD}/contrib_activity.png
mv ${SWIFTDIR}/contrib_stats.data ${ORIGPWD}/contrib_stats.data
mv ${SWIFTDIR}/swift_gerrit_history.patches ${ORIGPWD}/swift_gerrit_history.patches
mv ${SWIFTDIR}/percent_active.data ${ORIGPWD}/percent_active.data
cd ${ORIGPWD}
