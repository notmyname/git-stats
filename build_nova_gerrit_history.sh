#/bin/bash

PAGE_SIZE=500

# grab comments
PATCHES="nova_gerrit_history.patches"
QUERY="project:openstack/nova branch:master limit:$PAGE_SIZE --comments --all-reviewers is:mergeable"
ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON $QUERY >$PATCHES
MORE=`tail -20 $PATCHES | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep moreChanges | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`
I=1
while [[ $MORE == "true" ]]; do
    START=$((I * PAGE_SIZE))
    ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON $QUERY --start=$START >>$PATCHES
    MORE=`tail -20 $PATCHES | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep moreChanges | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`
    I=$((I+1))
done

# comments on open patches that aren't WIP
PATCHES="nova-open-comments.patches"
QUERY="project:openstack/nova branch:master status:open NOT label:Workflow\<=-1 limit:$PAGE_SIZE --comments --all-reviewers is:mergeable"
ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON $QUERY >$PATCHES
MORE=`tail -20 $PATCHES | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep moreChanges | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`
I=1
while [[ $MORE == "true" ]]; do
    START=$((I * PAGE_SIZE))
    ssh -p29418 notmyname@review.openstack.org gerrit query --format JSON $QUERY --start=$START >>$PATCHES
    MORE=`tail -20 $PATCHES | sed -e 's/[{}]/''/g' | awk -v k="text" '{n=split($0,a,","); for (i=1; i<=n; i++) print a[i]}' | grep moreChanges | cut -d: -f2 | cut -d: -f2 | sed 's/"//g' | tail -1`
    I=$((I+1))
done
