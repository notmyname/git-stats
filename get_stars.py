#!/usr/bin/env python

# gets starred swift patches

import subprocess
import shlex
import json
import sys
from collections import Counter

cmd = (
'/usr/bin/ssh -p 29418 notmyname@review.openstack.org \'gerrit query '
'--format JSON starredby:"%s" status:open\''
)

REVIEWS_FILENAME = 'swift_gerrit_history.patches'
DATA_FILENAME = 'all_stars.data'

core_emails = (
    "me@not.mn",
    "sam@swiftstack.com",
    "cschwede@redhat.com",
    "clay.gerrard@gmail.com",
    "alistair.coles@hp.com",
    "darrell@swiftstack.com",
    "david.goetz@rackspace.com",
    "greglange@gmail.com",
    "matt@oliver.net.au",
    "mike@weirdlooking.com",
    "zaitcev@kotori.zaitcev.us",
    "paul.e.luse@intel.com",
    "tsuyuzaki.kota@lab.ntt.co.jp",
    "thiago@redhat.com",
    "joel.wright@sohonet.com",
)

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
                reviewers.add(reviewer['email'])
    return reviewers

contrib_emails = load_reviewers(REVIEWS_FILENAME)

def get_stars():
    all_stars = []
    subject_len_limit = 50
    len_contrib_emails = len(contrib_emails)
    print 'Total emails to get info for: %d' % len_contrib_emails
    for i, email in enumerate(contrib_emails):
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
                if 'swift' not in patch['project']:
                    continue
                subject = patch['subject']
                if len(subject) > subject_len_limit:
                    subject = subject[:(subject_len_limit - 3)] + '...'
                owner = patch['owner']['name']
                weight = 2 if email in core_emails else 1
                for _ in range(weight):
                    starred.append((patch['number'], subject, owner.title(), patch['status']))
            except KeyError:
                # last line
                pass
        all_stars.extend(starred)
    return all_stars

try:
    all_stars = [tuple(x) for x in json.load(open(DATA_FILENAME))]
except IOError:
    all_stars = get_stars()
    json.dump(all_stars, open(DATA_FILENAME, 'wb'))

# so now that we have the starred patches, count them
ctr = Counter(all_stars)
ordered = ctr.most_common()
template = '%s (%s) - %s - (count: %s)'
for patch, count in ordered:
    if count <= 2:
        continue
    number, subject, owner, status = patch
    print template % (subject, owner, number, count)
