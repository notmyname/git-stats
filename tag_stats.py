#!/usr/bin/env python

import shlex
import subprocess
import sys

from utils import RELEASES, date_range

first = ('001407b969bc12d48bd7f10960f84f519bb19111', '2010-07-12')
tags = [first] + [(tag, date) for (date, tag, cycle) in RELEASES] + [('review/alistair_coles/rev7', '2018-05-15')]
tag_pairs = zip(*[tags[x::1] for x in (0, 1)])
trigger = 'Total Physical Source Lines of Code (SLOC)'


def stats_at_tag(tag):
    code_line_count = 0
    test_line_count = 0

    cmd = 'git checkout %s' % tag
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cmd = 'git clean -fd'
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    cmd = 'sloccount swift'
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw, _ = p.communicate()
    for line in raw.split('\n'):
        if line.startswith(trigger):
            raw_line_count = line.strip().rsplit('=', 1)[1].strip().replace(',', '')
            code_line_count = int(raw_line_count)

    cmd = 'sloccount test'
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw, _ = p.communicate()
    for line in raw.split('\n'):
        if line.startswith(trigger):
            raw_line_count = line.strip().rsplit('=', 1)[1].strip().replace(',', '')
            test_line_count = int(raw_line_count)
    ratio = float(test_line_count) / float(code_line_count)
    return code_line_count, test_line_count, ratio



# code_line_count, test_line_count, ratio = stats_at_tag(tags[0])
# print tags[0], '-', '-', code_line_count, test_line_count, ratio

initial_code, initial_test, initial_ratio = stats_at_tag(first[0])

total_lines = initial_code + initial_test

all_rows = []
row = [first[1], 'Initial Commit', '', total_lines, initial_code, initial_test, initial_ratio, -initial_test]
print ','.join(str(x) for x in row)

for ((start_tag, d1), (end_tag, d2)) in tag_pairs:
    cmd = 'git diff --shortstat %s..%s' % (start_tag, end_tag)
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    raw, _ = p.communicate()
    file_count, insertions, deletions = raw.strip().split(',')
    insertions = int(insertions.strip().split(' ', 1)[0])
    deletions = int(deletions.strip().split(' ', 1)[0])
    line_change = insertions - deletions
    total_lines += line_change

    code_line_count, test_line_count, ratio = stats_at_tag(end_tag)
    row = [d2, end_tag, line_change, total_lines, code_line_count, test_line_count, ratio, -test_line_count]
    print ','.join(str(x) for x in row)
