#!/bin/bash

ORIGPWD=`pwd`
SWIFTDIR="$HOME/Documents/swift"

mv ${ORIGPWD}/contrib_stats2.data ${SWIFTDIR}/contrib_stats2.data 2>/dev/null
mv ${ORIGPWD}/swift_gerrit_history.patches ${SWIFTDIR}/swift_gerrit_history.patches 2>/dev/null

cd ${SWIFTDIR}
python "$ORIGPWD"/contrib_stats2.py $@
mv ${SWIFTDIR}/active_contribs2.png ${ORIGPWD}/active_contribs2.png
mv ${SWIFTDIR}/total_contribs2.png ${ORIGPWD}/total_contribs2.png
mv ${SWIFTDIR}/contrib_activity2.png ${ORIGPWD}/contrib_activity2.png
mv ${SWIFTDIR}/contrib_stats2.data ${ORIGPWD}/contrib_stats2.data
mv ${SWIFTDIR}/swift_gerrit_history.patches ${ORIGPWD}/swift_gerrit_history.patches
cd ${ORIGPWD}
