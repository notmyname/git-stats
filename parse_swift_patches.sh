#!/bin/bash
# grabs swift patches from gerrit

# grap open patches (that aren't WIP)
ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON project:openstack/swift branch:master status:open NOT label:Workflow\<=-1 >swift-open.patches

# grab closed patches
ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON project:openstack/swift branch:master status:closed NOT label:Workflow\<=-1 >swift-closed.patches

echo "Open Patches Stats:"
./patches_parser.py swift-open.patches
echo
echo
echo "Closed Patches Stats:"
./patches_parser.py swift-closed.patches
