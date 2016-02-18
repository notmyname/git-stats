#!/usr/bin/env python

# builds the swift community dashboard

from datetime import datetime, timedelta

import review_timings
import stats
import get_stars

TEMPLATE = 'dash_template.html'
REVIEWS_FILENAME = 'swift-open-comments.patches'
OUTPUT_FILENAME = 'swift_community_dashboard.html'

template_vars = {
    'open_patches': '',        # number of open patches
    'owner_response': '',      # patch owner response time
    'reviewer_response': '',    # patch reviewer response time
    'winner': '',             # who's winning? patch owners or reviewers?
    'unreviewed_patches': '',  # number of unreviewed patches
    'community_stars': '',     # html snippet for unreviewed patches info
    'current_time': '',        # timestamp when this dashboard was created
}

template_vars['current_time'] = datetime.strftime(datetime.now(),
                                                  '%H:%M:%S %h %d, %Y')

timing_data, unreviewed_patchnums = review_timings.load_data(REVIEWS_FILENAME)

owner_data = [x[0] for x in timing_data.itervalues()]
reviewer_data = [x[1] for x in timing_data.itervalues()]

template_vars['open_patches'] = '%d' % len(timing_data.keys())
template_vars['unreviewed_patches'] = '%d' % len(unreviewed_patchnums)
owner_time = timedelta(seconds=stats.median(owner_data))
reviewer_time = timedelta(seconds=stats.median(reviewer_data))
if owner_time < reviewer_time:
    template_vars['winner'] = 'Owners'
else:
    template_vars['winner'] = 'Reviewers'
template_vars['owner_response'] = str(owner_time)
template_vars['reviewer_response'] = str(reviewer_time)

patch_tmpl = '<li><a href="https://review.openstack.org/#/c/{number}/">' \
             '<span class="subject">{subject}</span> ' \
             '<span class="owner">{owner}</span></a></li>'
out = []
community_starred_patches = get_stars.get_ordered_patches()
for i, (patch, count) in enumerate(community_starred_patches):
    if i >= 20:
        break
    number, subject, owner, status = patch
    out.append(patch_tmpl.format(number=number, subject=subject, owner=owner))
template_vars['community_stars'] = '\n'.join(out)

tmpl = open(TEMPLATE, 'rb').read()
with open(OUTPUT_FILENAME, 'wb') as f:
    f.write(tmpl.format(**template_vars))
