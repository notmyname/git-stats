#!/bin/bash

set -e

ORIGPWD=`pwd`
cd /Users/john/Documents/git-stats

# clear out old data
rm -f all_stars.data

# get reviewer history
./build_swift_gerrit_history.sh

# get swift history and build weightings
./swift_contrib_stats.sh

# rebuild "most starred" list
./get_stars.sh

# rebuild the dashboard
./create_and_deploy_dash.sh

echo 'recreated all stats'

cd ${ORIGPWD}
