# vcs_authors is the output of `git shortlog -nes`

import sys

ignored_authors = [  # known bots, not real people
    ('OpenStack Proposal Bot', 'openstack-infra@lists.openstack.org'),
    ('Jenkins', 'jenkins@review.openstack.org'),
    ('OpenStack Jenkins', 'jenkins@openstack.org'),
    ('Cloud User', 'cloud-user@bounce.cisco.com'),  # might be anne gentle, not sure
    ('OpenStack Release Bot', 'infra-root@openstack.org'),
]

authors = [x.strip() for x in open(sys.argv[2], 'rb').readlines()]
author_by_name = {}
author_by_email = {}
for line in authors:
    try:
        name, email = line.rsplit('(', 1)
    except ValueError:
        continue
    name = name.strip()
    email = email.replace(')', '').strip()
    author_by_email[email] = name
    author_by_name[name] = email

authors = [x.strip() for x in open(sys.argv[1], 'rb').readlines()]
vcs_authors = []
for line in authors:
    name, email = line.split('<')
    name = name.split('\t', 1)[1].strip()
    email = email.replace('>', '').strip()
    vcs_authors.append((name, email))

for name, email in vcs_authors:
    if (name, email) in ignored_authors:
        continue
    if email not in author_by_email:
        print 'MISSING: %s (%s)' % (name, email)
        if name in author_by_name:
            print '  same name (%s) but different email (%s vs %s) in AUTHORS' \
                % (name, email, author_by_name[name])
    elif name not in author_by_name:
            print '  same email (%s) but different name (%s vs %s) in AUTHORS' \
                % (email, name, author_by_email[email])

# track names that are in AUTHORS but not in vcs
credited_but_no_commits = []
for email, name in author_by_email.items():
    if (name, email) not in vcs_authors:
        credited_but_no_commits.append((name, email))
if credited_but_no_commits:
    print '-' * 8 + 'Credited authors with no commits' + '-' * 8
    print '\n'.join('%s (%s)' % (n,e) for (n,e) in credited_but_no_commits)
