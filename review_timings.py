#!/usr/bin/env python

# get review comment timings

import json
import datetime
import sys
from collections import defaultdict

from ascii_graph import Pyasciigraph

import stats

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

def load_data(filename, subject_len_limit=50):
    patch_data = {}
    unreviewed_patches = []
    no_follow_ups = []
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
                if review_comment['reviewer']['name'].endswith(' CI'):
                    continue
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
            owner = review_data['owner']['name']
            subject = review_data['subject']
            if len(subject) > subject_len_limit:
                subject = subject[:(subject_len_limit - 3)] + '...'
            if owner_deltas:
                owner_avg = float(sum(owner_deltas)) / len(owner_deltas)
            else:
                owner_avg = 0
                no_follow_ups.append((patch_number, subject, owner, review_data['status']))
            if reviewer_deltas:
                reviewer_avg = float(sum(reviewer_deltas)) / len(reviewer_deltas)
            else:
                # no reviews ever!
                reviewer_avg = 0
                unreviewed_patches.append((patch_number, subject, owner, review_data['status']))
                # print patch_number
            if any((owner_avg, reviewer_avg)):
                patch_data[patch_number] = (owner_avg, reviewer_avg)
    return patch_data, unreviewed_patches, no_follow_ups

def histogram(data, name):
    name = 'count of %s response time by week' % name
    g = Pyasciigraph()
    buckets = defaultdict(int)
    for item in data:
        buckets[int(item // (86400 * 7))] += 1
    for line in g.graph(name, ((k, v) for k, v in buckets.iteritems())):
        print line

if __name__ == '__main__':
    REVIEWS_FILENAME = 'swift-open-comments.patches'
    if '--all-patches' in sys.argv:
        REVIEWS_FILENAME = 'swift_gerrit_history.patches'
    timing_data, unreviewed, owner_no_follow_ups = load_data(REVIEWS_FILENAME)

    # REVIEWS_FILENAME = 'swiftclient-open-comments.patches'
    # if '--all-patches' in sys.argv:
    #     REVIEWS_FILENAME = 'swiftclient_gerrit_history.patches'
    # client_timing_data, client_unreviewed, client_owner_no_follow_ups = load_data(REVIEWS_FILENAME)

    # timing_data.update(client_timing_data)
    # unreviewed.extend(client_unreviewed)

    owner_data = [x[0] for x in timing_data.itervalues()]
    reviewer_data = [x[1] for x in timing_data.itervalues()]

    histogram(owner_data, 'owner')
    histogram(reviewer_data, 'reviewer')

    print 'Stats for %d patches' % len(timing_data.keys())
    print 'Patch owner review stats:'
    print ' mean: %s' % str(datetime.timedelta(seconds=stats.mean(owner_data)))
    print ' median: %s' % str(datetime.timedelta(seconds=stats.median(owner_data)))
    print ' std_deviation: %s' % str(datetime.timedelta(seconds=stats.std_deviation(owner_data)))
    print ' max_difference: %s' % str(datetime.timedelta(seconds=stats.min_max_difference(owner_data)))
    print ' %d patches with no follow-up' % len(owner_no_follow_ups)
    print
    print 'Patch reviewer stats:'
    print ' mean: %s' % str(datetime.timedelta(seconds=stats.mean(reviewer_data)))
    print ' median: %s' % str(datetime.timedelta(seconds=stats.median(reviewer_data)))
    print ' std_deviation: %s' % str(datetime.timedelta(seconds=stats.std_deviation(reviewer_data)))
    print ' max_difference: %s' % str(datetime.timedelta(seconds=stats.min_max_difference(reviewer_data)))
    print ' %d unreviewed patches' % len(unreviewed)
    if '--show-unreviewed' in sys.argv:
        for patch_number in unreviewed:
            print 'https://review.openstack.org/#/c/%d/' % patch_number
