#!/bin/bash

set -e

ORIGPWD=`pwd`
cd /Users/john/Documents/git-stats

# get commit history
./get_commit_history.sh

# get reviewer history
./build_swift_gerrit_history.sh

# build weightings and graphs
./swift_contrib_stats.sh

# rebuild the dashboard
./make_dashboard.py

# upload the dashboard
/Users/john/bin/deploy_swift_dash

echo 'dashboard recreated and deployed'

cd ${ORIGPWD}
