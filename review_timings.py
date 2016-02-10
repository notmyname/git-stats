#!/usr/bin/env python

# get review comment timings

import json
import datetime

# REVIEWS_FILENAME = 'swift_gerrit_history.patches'
REVIEWS_FILENAME = 'swift-open-comments.patches'

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

def load_data(filename):
    patch_data = {}
    with open(filename, 'rb') as f:
        for line in f:
            if line:
                review_data = json.loads(line)
            else:
                continue
            if 'comments' not in review_data:
                continue
            try:
                owner = review_data['owner']['email']
            except KeyError:
                continue
            if owner in bots:
                continue
            patch_number = int(review_data['number'])
            comment_times_and_types = []
            for review_comment in review_data['comments']:
                try:
                    reviewer = review_comment['reviewer']['email']
                except KeyError:
                    continue
                message = review_comment['message']
                timestamp = review_comment['timestamp']
                if reviewer in bots:
                    continue
                comment_times_and_types.append((reviewer == owner, timestamp))
            if not comment_times_and_types:
                continue
            recent_timestamp = comment_times_and_types[0][1]  # should use min?
            owner_deltas = []
            reviewer_deltas = []
            last_is_owner = True  # assumes the first comment is from the author
            for is_owner, timestamp in comment_times_and_types:
                delta = timestamp - recent_timestamp
                if is_owner and not last_is_owner:
                    owner_deltas.append(delta)
                elif not is_owner and last_is_owner:
                    reviewer_deltas.append(delta)
                else:
                    # This is a comment from the same type of person as the
                    # last comment on this patch. Or the first comment on it.
                    pass
                recent_timestamp = timestamp
                last_is_owner = is_owner
            if owner_deltas:
                owner_avg = float(sum(owner_deltas)) / len(owner_deltas)
            else:
                owner_avg = 0
            if reviewer_deltas:
                reviewer_avg = float(sum(reviewer_deltas)) / len(reviewer_deltas)
            else:
                reviewer_avg = 0
            patch_data[patch_number] = (owner_avg, reviewer_avg)
    return patch_data

timing_data = load_data(REVIEWS_FILENAME)

global_owner_avg = 0
global_reviewer_avg = 0
for patch_num, (owner_avg, reviewer_avg) in timing_data.iteritems():
    global_owner_avg += owner_avg
    global_reviewer_avg += reviewer_avg
    oa = datetime.timedelta(seconds=owner_avg)
    ra = datetime.timedelta(seconds=reviewer_avg)
    print 'Patch %d\n owner: %s\n reviewer: %s' % (patch_num, oa, ra)
global_owner_avg /= len(timing_data)
global_reviewer_avg /= len(timing_data)
oa = datetime.timedelta(seconds=global_owner_avg)
ra = datetime.timedelta(seconds=global_reviewer_avg)
print 'Global average:\n owner: %s\n reviewer: %s' % (oa, ra)
