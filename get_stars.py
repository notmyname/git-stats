#!/usr/bin/env python

# gets starred swift patches

import subprocess
import shlex
import json
import sys
from collections import Counter, defaultdict

cmd = (
'/usr/bin/ssh -p 29418 notmyname@review.openstack.org \'gerrit query '
'--format JSON starredby:"%s" status:open\''
)

REVIEWS_FILENAME = 'swift_gerrit_history.patches'
DATA_FILENAME = 'all_stars.data'
PERCENT_ACTIVE_FILENAME = 'percent_active.data'

def load_reviewers(filename):
    reviewers = set()
    with open(filename, 'rb') as f:
        for line in f:
            if line:
                review_data = json.loads(line)
            else:
                continue
            if 'comments' not in review_data:
                continue
            for review_comment in review_data['comments']:
                reviewer = review_comment['reviewer']
                if 'email' not in reviewer:
                    continue
                reviewers.add((reviewer['email'], reviewer['name'].lower()))
    return reviewers

contrib_emails = load_reviewers(REVIEWS_FILENAME)

def load_weights(filename):
    weights = {}
    with(open(filename, 'rb')) as f:
        for line in f:
            if line:
                person, percent = line.split(':')
                person = person.strip()
                percent = float(percent)
                weights[person.lower()] = percent
    return weights

weights = load_weights(PERCENT_ACTIVE_FILENAME)

def load_starred_patches():
    all_stars = defaultdict(list)
    subject_len_limit = 50
    len_contrib_emails = len(contrib_emails)
    print 'Total emails to get info for: %d' % len_contrib_emails
    for i, (email, starer_name) in enumerate(contrib_emails):
        print '%d/%d %s' % (i + 1, len_contrib_emails, email)
        args = shlex.split(cmd % email)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        raw, _ = p.communicate()
        starred = []
        for line in raw.split('\n'):
            try:
                patch = json.loads(line)
            except ValueError:
                # last line
                break
            try:
                if 'openstack/swift' not in patch['project']:
                    continue
                subject = patch['subject']
                if len(subject) > subject_len_limit:
                    subject = subject[:(subject_len_limit - 3)] + '...'
                owner = patch['owner']['name']
                starred.append((patch['number'], subject, owner.title(), patch['status']))
            except KeyError:
                # last line
                pass
        all_stars[starer_name].extend(starred)
    return all_stars

def weight_stars(stars_by_starer):
    all_stars = []
    for starer_name, star_list in stars_by_starer.iteritems():
        weight = max(int(weights.get(starer_name, 0.0) * 100), 1)
        starred = []
        for number, subject, owner, status in star_list:
            for _ in range(weight):
                starred.append((number, subject, owner.title(), status))
        all_stars.extend(starred)
    return all_stars

try:
    stars_by_starer = json.load(open(DATA_FILENAME))
except IOError:
    stars_by_starer = load_starred_patches()
    json.dump(stars_by_starer, open(DATA_FILENAME, 'wb'))

all_stars = weight_stars(stars_by_starer)

# so now that we have the starred patches, count them
ctr = Counter(all_stars)
ordered = ctr.most_common()
template = '%s (%s) - %s - (count: %s)'
for i, (patch, count) in enumerate(ordered):
    if i > 20:
        break
    number, subject, owner, status = patch
    print template % (subject, owner, number, count)
