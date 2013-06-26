# vcs_authors is the output of `git shortlog -nes --no-merges`

import sys

authors = [x.strip() for x in open('/Users/john/Documents/swift/AUTHORS', 'rb').readlines()]
credited_authors = {}
author_by_name = {}
author_by_email = {}
for line in authors:
    try:
        name, email = line.split('(')
    except ValueError:
        continue
    name = name.strip()
    email = email.replace(')', '').strip()
    author_by_email[email] = name
    author_by_name[name] = email
    credited_authors[email] = name

authors = [x.strip() for x in open('vcs_authors', 'rb').readlines()]
vcs_authors = []
for line in authors:
    name, email = line.split('<')
    name = name.split('\t', 1)[1].strip()
    email = email.replace('>', '').strip()
    vcs_authors.append((name, email))

for name, email in vcs_authors:
    if email not in author_by_email:
        print '%s (%s)' % (name, email)
        if name in author_by_name:
            print '  same name with different email in credited_authors (%s)' \
                % author_by_name[name]
