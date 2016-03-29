#!/usr/bin/env python

# builds the swift community dashboard

from datetime import datetime, timedelta

import review_timings
import stats
import get_stars
from utils import PERCENT_ACTIVE_FILENAME, \
    CLIENT_REVIEWS_FILENAME

REVIEWS_FILENAME = 'swift-open-comments.patches'

TEMPLATE = 'dash_template.html'
OUTPUT_FILENAME = 'swift_community_dashboard.html'

template_vars = {
    'open_patches': '',        # number of open patches
    'owner_response': '',      # patch owner response time
    'reviewer_response': '',   # patch reviewer response time
    'winner': '',              # who's winning? patch owners or reviewers?
    'unreviewed_patches': '',  # number of unreviewed patches
    'community_stars': '',     # html snippet for community starred patches
    'current_time': '',        # timestamp when this dashboard was created
    'unreviewed_list': '',     # html snippet for unreviewed patches
    'no_follow_ups': '',       # number of patches that have no owner follow up after review
    'total_contributors': '',  # total number of contributors
    'active_contributors': '', # number of active contributors
}

template_vars['current_time'] = datetime.strftime(datetime.now(),
                                                  '%H:%M:%S %h %d, %Y')

timing_data, unreviewed_patchnums, owner_no_follow_ups = review_timings.load_data(REVIEWS_FILENAME)
client_timing_data, client_unreviewed_patchnums, client_owner_no_follow_ups = review_timings.load_data(CLIENT_REVIEWS_FILENAME)

# timing_data.update(client_timing_data)

# trim off the top and bottom few percent
outliers = int(len(timing_data) * .1) // 2
owner_data = sorted([x[0] for x in timing_data.itervalues()])[outliers:-outliers]
reviewer_data = sorted([x[1] for x in timing_data.itervalues()])[outliers:-outliers]

template_vars['open_patches'] = '%d' % len(timing_data.keys())
template_vars['unreviewed_patches'] = '%d' % (len(unreviewed_patchnums) )#+ len(client_unreviewed_patchnums))
template_vars['no_follow_ups'] = '%d' % (len(owner_no_follow_ups) )#+ len(client_owner_no_follow_ups))
owner_time = timedelta(seconds=stats.median(owner_data))
reviewer_time = timedelta(seconds=stats.median(reviewer_data))
if owner_time < reviewer_time:
    template_vars['winner'] = 'Owners'
else:
    template_vars['winner'] = 'Reviewers'
template_vars['owner_response'] = str(owner_time)
template_vars['reviewer_response'] = str(reviewer_time)

with open(PERCENT_ACTIVE_FILENAME, 'rb') as f:
    total_contributors = len(f.readlines())
template_vars['total_contributors'] = total_contributors

template_vars['active_contributors'] = 18

patch_tmpl = '<li><a href="https://review.openstack.org/#/c/{number}/">' \
             '<span class="subject">{subject}</span> - ' \
             '<span class="project">{project}</span> - ' \
             '<span class="owner">{owner}</span></a></li>'
out = []
community_starred_patches = get_stars.get_ordered_patches()
for i, (patch, count) in enumerate(community_starred_patches):
    if i >= 20:
        break
    number, subject, owner, status = patch
    out.append(patch_tmpl.format(number=number, subject=subject, owner=owner, project=''))
template_vars['community_stars'] = '\n'.join(out)

out = []
for num, subject, owner, status in reversed(unreviewed_patchnums):
    out.append(patch_tmpl.format(number=num, subject=subject, owner=owner.encode('utf8'), project='swift'))
# for num, subject, owner, status in reversed(client_unreviewed_patchnums):
#     out.append(patch_tmpl.format(number=num, subject=subject, owner=owner.encode('utf8'), project='swiftclient'))
template_vars['unreviewed_list'] = '\n'.join(out)

tmpl = open(TEMPLATE, 'rb').read()
with open(OUTPUT_FILENAME, 'wb') as f:
    f.write(tmpl.format(**template_vars))
