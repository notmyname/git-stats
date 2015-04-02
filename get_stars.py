#!/usr/bin/env python

# gets starred swift patches

import subprocess
import shlex
import json
import sys

GERRIT_USERNAME = 'notmyname'
try:
    GERRIT_USERNAME = sys.argv[1]
except IndexError:
    pass

cmd = (
'/usr/bin/ssh -p 29418 %s@review.openstack.org \'gerrit query '
'--format JSON '
'(starredby:notmyname'
#' OR starredby:torgomatic'
#' OR starredby:cschwede'
#' OR starredby:"alistair.coles@hp.com"'
#' OR starredby:"darrell@swiftstack.com"'
#' OR starredby:"david.goetz@rackspace.com"'
#' OR starredby:"greglange@gmail.com"'
#' OR starredby:"matt@oliver.net.au"'
#' OR starredby:"mike@weirdlooking.com"'
#' OR starredby:"zaitcev@kotori.zaitcev.us"'
#' OR starredby:"paul.e.luse@intel.com"'
')\''
) % GERRIT_USERNAME

args = shlex.split(cmd)
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
        starred.append({'owner': owner.title(),
                        'subject': subject,
                        'url': patch['url'],
                        'number': patch['number'],
                        'status': patch['status']})
    except KeyError:
        # last line
        pass


template = '%(subject)s (%(owner)s) - patch %(number)s - (%(status)s)'
for item in starred:
    print template % item
