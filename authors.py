# vcs_authors is the output of `git shortlog -nes --no-merges`

import sys

authors = [x.strip() for x in open('/Users/john/Documents/swift/AUTHORS', 'rb').readlines()]
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

authors = [x.strip() for x in open('vcs_authors', 'rb').readlines()]
vcs_authors = []
for line in authors:
    name, email = line.split('<')
    name = name.split('\t', 1)[1].strip()
    email = email.replace('>', '').strip()
    vcs_authors.append((name, email))

for name, email in vcs_authors:
    if email not in author_by_email:
        print 'MISSING: %s (%s)' % (name, email)
        if name in author_by_name:
            print '  same name (%s) but different email (%s vs %s) in AUTHORS (%s)' \
                % (name, email, author_by_name[name])
    elif name not in author_by_name:
            print '  same email (%s) but different name (%s vs %s) in AUTHORS' \
                % (email, name, author_by_email[email])

# TODO: track names that are in AUTHORS but not in vcs
