#!/usr/bin/env python

from collections import defaultdict
import re

pattern = r'[0-9a-f]{7}\s{1}'
regex = re.compile(pattern)

# built with:
# git log --pretty="tformat:%h %ai %s" --name-only
FILENAME = '/Users/john/swift_history.txt'


commits = defaultdict(list)

with open(FILENAME, 'rb') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if regex.search(line):
            commit = line
        else:
            #path
            commits[commit].append(line)

count = 0
for c, f in commits.items():
    if len(f) < 2:
        continue
    target_count = 0
    touches_proxy =False
    for fn in f:
        if 'swift/proxy/' in fn:
            touches_proxy = True
            break
    if touches_proxy:
        touches_storage = False
        for fn in f:
            if 'swift/obj/' in fn or \
               'swift/container/' in fn or \
               'swift/account/' in fn:
                    touches_storage = True
        if touches_storage:
            count += 1
            print c

print '%d commits touched both the proxy and storage servers' % count
