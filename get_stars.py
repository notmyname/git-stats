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

all_stars = []
for email in core_emails:
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
            subject = patch['subject']
            limit = 50
            if len(subject) > limit:
                subject = subject[:(limit - 3)] + '...'
            owner = patch['owner']['name']
            starred.append((patch['url'], subject, owner.title(), patch['status']))
        except KeyError:
            # last line
            pass
    all_stars.extend(starred)

# so now that we have the starred patches, count them
ctr = Counter(all_stars)
ordered = ctr.most_common()
template = '%s (%s) - %s - (count: %s)'
for patch, count in ordered:
    if count <= 1:
        continue
    url, subject, owner, status = patch
    print template % (subject, owner, url, count)
