# git log --format='%h' --shortstat --no-merges 1.4.8.. | python ./big_commit.py

import sys
from collections import defaultdict

commits_by_diff = defaultdict(int)
commit_hash = ''
for line in sys.stdin:
    line = line.strip()
    if line:
        parts = line.split()
        if len(parts) == 1:
            commit_hash = parts[0]
        else:
            try:
                commits_by_diff[commit_hash] = int(parts[3]) - int(parts[5])
            except IndexError:
                commits_by_diff[commit_hash] = int(parts[3])

for s,h in reversed(sorted((y,x) for x,y in commits_by_diff.items())):
    print h, s
