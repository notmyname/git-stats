#!/usr/bin/env python

from collections import defaultdict
import json

from utils import REVIEWS_FILENAME as ALL_PATCHES_FILENAME
from parse_commits_into_json import load_commits
from contrib_stats import load_reviewers
from get_stars import weights, get_stars_by_starer, get_ordered_patches

REVIEWS_FILENAME = 'swift-open-comments.patches'

reviewers_by_date = load_reviewers(REVIEWS_FILENAME)
authors_by_date, ts_by_person = load_commits()
stars_by_starer = get_stars_by_starer()

all_contributors = set()
all_contributors.update(ts_by_person.keys())
for d in reviewers_by_date:
    all_contributors.update(reviewers_by_date[d])


len(all_contributors)  # why is this so much smaller than the total number in the other script?


bots = (
    'jenkins@review.openstack.org',
    'openstack-infra@lists.openstack.org',
    'jenkins@openstack.org',
    'openstack-ci@swiftstack.com',
    'mike+goci@weirdlooking.com',
    'trivial-rebase@review.openstack.org',
    'coraid-openstack-ci-all@mirantis.com',
    'review@openstack.org',
)

reviews_by_person = defaultdict(list)
patches_by_person = defaultdict(list)
patch_info = {}  # patch_num: (subject, owner, [reviewers])
subject_len_limit = 50
with open(REVIEWS_FILENAME, 'rb') as f:
    for line in f:
        if line:
            review_data = json.loads(line)
        else:
            continue
        if 'comments' not in review_data:
            continue
        owner = review_data['owner'].get('email')
        if owner is None or owner in bots:
            continue
        patch_number = int(review_data['number'])
        subject = review_data['subject']
        if len(subject) > subject_len_limit:
            subject = subject[:(subject_len_limit - 3)] + '...'
        patches_by_person[owner].append(patch_number)
        patch_reviewers = []
        for approval in review_data['currentPatchSet'].get('approvals', []):
            reviewer = approval['by'].get('email') or approval['by'].get('username')
            # if reviewer is None or reviewer in bots:
            #     print approval
            #     continue
            if approval['description'] in ('Code-Review', ):
                reviews_by_person[reviewer].append((patch_number, int(approval['value'])))
                patch_reviewers.append((reviewer, int(approval['value'])))
            elif approval['type'] in ('Verified', ) and int(approval['value']) < 0:
                reviews_by_person[reviewer].append((patch_number, int(approval['value'])))
                patch_reviewers.append((reviewer, int(approval['value'])))
        patch_info[patch_number] = (subject, owner, patch_reviewers)



person_info = {}  # person: (weight, [starred], [reviews], [owned])


for person in all_contributors:
    name, email = person.split('<', 1)
    name = name.strip()
    norm_name = name.lower()
    email = email.strip('>').strip()
    w = weights.get(norm_name)
    person_info[email] = (
        w,
        [int(x[0]) for x in stars_by_starer.get(norm_name, [])],
        reviews_by_person.get(email, []),
        patches_by_person.get(email, []),
        name,
        email,
    )


#TODO serialize patch_info and person_info. make it callable as a library. sort lists of patches


# email = 'tim@swiftstack.com'
#email = 'tim.burke@gmail.com'
# email = 'richard.hawkins@rackspace.com'
# email = 'kellerbr@us.ibm.com'
# email = 'me@not.mn'
# email = 'jrichli@us.ibm.com'
# email = 'alistair.coles@hpe.com'
#email = 'clay.gerrard@gmail.com'
email = 'mahati.chamarthy@gmail.com'

weight, stars, reviews, owned, name, _ = person_info[email]
print 'What should %s work on?' % name
out = []
for p in stars:
    if p not in patch_info:
        continue
    subject, owner, reviewers = patch_info[p]
    if email not in (x[0] for x in reviewers) and owner != email:
        out.append(' - https://review.openstack.org/#/c/%d/ "%s" (owned by %s)' % (p, subject, person_info[owner][4]))
if out:
    print 'Starred patches that need a review:'
    print '\n'.join(out)
out = []
for p in owned:
    if p not in patch_info:
        continue
    subject, owner, reviewers = patch_info[p]
    if reviewers:
        has_negative_review = any((x[1]<0 for x in reviewers))
        # for r, vote in reviewers:
        #     for patch_num, vote in person_info[r][2]:
        #         if p == patch_num and vote <= 0:
        #             has_negative_review = True
        #             break
        #     if has_negative_review:
        #         break
        if has_negative_review:
            out.append(' - https://review.openstack.org/#/c/%d/ "%s"' % (p, subject))
if out:
    print 'Owned patches that need follow-up:'
    print '\n'.join(out)
out = []
for p, w in get_ordered_patches():
    p = int(p[0])
    if p not in patch_info:
        continue
    subject, owner, reviewers = patch_info[p]
    if owner == email or email in (x[0] for x in reviewers):
        continue
    negative_reviews = [True for x in reviewers if x[1]<0]
    if not any(negative_reviews):
        out.append(' - https://review.openstack.org/#/c/%d/ "%s"' % (p, subject))
        if len(out) >= 5:
            break
if out:
    print 'Community starred patches that need reviews:'
    print '\n'.join(out)


# need to have "patches I've previously reviewed and have a new patch set now"
# probably need to get every review from gerrit instead of just the last patch set
