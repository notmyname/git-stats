#!/usr/bin/env python

# get review comment timings

import json
import datetime
import sys

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
            if owner_deltas:
                owner_avg = float(sum(owner_deltas)) / len(owner_deltas)
            else:
                owner_avg = 0
            if reviewer_deltas:
                reviewer_avg = float(sum(reviewer_deltas)) / len(reviewer_deltas)
            else:
                # no reviews ever!
                reviewer_avg = 0
                subject = review_data['subject']
                owner = review_data['owner']['name']
                subject = review_data['subject']
                if len(subject) > subject_len_limit:
                    subject = subject[:(subject_len_limit - 3)] + '...'
                unreviewed_patches.append((patch_number, subject, owner, review_data['status']))
                # print patch_number
            if any((owner_avg, reviewer_avg)):
                patch_data[patch_number] = (owner_avg, reviewer_avg)
    return patch_data, unreviewed_patches

if __name__ == '__main__':
    project = 'swift'
    if '--nova' in sys.argv:
        project = 'nova'
    REVIEWS_FILENAME = '%s-open-comments.patches' % project
    if '--all-patches' in sys.argv:
        REVIEWS_FILENAME = '%s_gerrit_history.patches' % project

    timing_data, unreviewed = load_data(REVIEWS_FILENAME)

    owner_data = [x[0] for x in timing_data.itervalues()]
    reviewer_data = [x[1] for x in timing_data.itervalues()]

    print 'Stats for %d patches' % len(timing_data.keys())
    print 'Patch owner review stats:'
    print ' mean: %s' % str(datetime.timedelta(seconds=stats.mean(owner_data)))
    print ' median: %s' % str(datetime.timedelta(seconds=stats.median(owner_data)))
    print ' std_deviation: %s' % str(datetime.timedelta(seconds=stats.std_deviation(owner_data)))
    print ' max_difference: %s' % str(datetime.timedelta(seconds=stats.min_max_difference(owner_data)))
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
