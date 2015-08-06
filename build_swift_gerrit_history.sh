#/bin/bash

ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON project:openstack/swift --comments limit:500 >swift_gerrit_history.patches


LAST=`tail -20 swift_gerrit_history.patches | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep sortKey | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`

OLDLAST=''

while [[ $OLDLAST != $LAST ]]; do
    OLDLAST=$LAST


    ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON project:openstack/swift --comments limit:500 resume_sortkey:$LAST >>swift_gerrit_history.patches

    LAST=`tail -20 swift_gerrit_history.patches | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep sortKey | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`

    echo $LAST, $OLDLAST
done
