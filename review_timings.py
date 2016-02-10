#!/usr/bin/env python

# get review comment timings

import json
import datetime
import sys

REVIEWS_FILENAME = 'swift-open-comments.patches'
if '--all-patches' in sys.argv:
    REVIEWS_FILENAME = 'swift_gerrit_history.patches'

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
            if any((owner_avg, reviewer_avg)):
                patch_data[patch_number] = (owner_avg, reviewer_avg)
    return patch_data

timing_data = load_data(REVIEWS_FILENAME)


#######################################################################

import math
import collections

def mean(data):
    return float(sum(data)) / float(len(data))

def median(data):
    count = len(data)
    if count % 2:
        return data[count / 2]
    else:
        middle = count // 2
        return sum(data[middle-1:middle+1]) / 2.0

def mode(data):
    d = collections.defaultdict(int)
    for item in data:
        d[item] += 1
    return max((count,key) for key,count in d.items())[1]

def std_deviation(data):
    avg = mean(data)
    avg_squared_deviation = mean([(avg-x)**2 for x in data])
    return math.sqrt(avg_squared_deviation)

def min_max_difference(data):
    data = data[:]
    data.sort()
    return data[-1] - data[0]

def stats(data):
    return (mean(data),
            median(data),
            mode(data),
            std_deviation(data),
            min_max_difference(data),
           )

#######################################################################

owner_data = [x[0] for x in timing_data.itervalues()]
reviewer_data = [x[1] for x in timing_data.itervalues()]

print 'Patch owner review stats:'
print ' mean: %s' % str(datetime.timedelta(seconds=mean(owner_data)))
print ' median: %s' % str(datetime.timedelta(seconds=median(owner_data)))
print ' std_deviation: %s' % str(datetime.timedelta(seconds=std_deviation(owner_data)))
print ' max_difference: %s' % str(datetime.timedelta(seconds=min_max_difference(owner_data)))
print
print 'Patch reviewer stats:'
print ' mean: %s' % str(datetime.timedelta(seconds=mean(reviewer_data)))
print ' median: %s' % str(datetime.timedelta(seconds=median(reviewer_data)))
print ' std_deviation: %s' % str(datetime.timedelta(seconds=std_deviation(reviewer_data)))
print ' max_difference: %s' % str(datetime.timedelta(seconds=min_max_difference(reviewer_data)))
