#!/bin/bash

set -e

ORIGPWD=`pwd`
cd /Users/john/Documents/git-stats

# update gerrit stats
./build_swift_gerrit_history.sh

# rebuild the dashboard
./make_dashboard.py

# upload the dashboard
deploy_swift_dash

echo 'dashboard recreated and deployed'

cd ${ORIGPWD}
