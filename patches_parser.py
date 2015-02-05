#!/usr/bin/env python

import sys
import json
from collections import defaultdict
import time
import datetime




#######################################################################

import math
import collections

def mean(data):
    return float(sum(data)) / float(len(data))

def median(data):
    count = len(data)
    if count % 2:
        return data[count / 2]
    else:
        middle = count // 2
        return sum(data[middle-1:middle+1]) / 2.0

def mode(data):
    d = collections.defaultdict(int)
    for item in data:
        d[item] += 1
    return max((count,key) for key,count in d.items())[1]

def std_deviation(data):
    avg = mean(data)
    avg_squared_deviation = mean([(avg-x)**2 for x in data])
    return math.sqrt(avg_squared_deviation)

def min_max_difference(data):
    data = data[:]
    data.sort()
    return data[-1] - data[0]

def stats(data):
    return (mean(data),
            median(data),
            mode(data),
            std_deviation(data),
            min_max_difference(data),
           )

#######################################################################




patches_input = sys.argv[1]

patches = defaultdict(list)
count = 0
biggest = 0
big = None
with open(patches_input) as f:
    for line in f:
        parsed = json.loads(line)
        try:
            owner = parsed['owner']['email']
            start = int(parsed['createdOn'])
            if parsed['open']:
                end = time.time()
            else:
                end = int(parsed['lastUpdated'])
            patches[owner].append((start, end))
            count += 1
            x = end - start
            if x > biggest:
                biggest = x
                big = parsed
        except KeyError:
            pass  # last line is gerrit query stats

all_durations = []
for owner, times in patches.items():
    durations = [(e - s) for s, e in times]
    all_durations.extend(durations)


print 'count: %d' % count
print 'mean: %s' % str(datetime.timedelta(seconds=mean(all_durations)))
print 'median: %s' % str(datetime.timedelta(seconds=median(all_durations)))
print 'std_deviation: %s' % str(datetime.timedelta(seconds=std_deviation(all_durations)))
print str(datetime.timedelta(seconds=biggest))
print big


# how many patches open
# patch that is the longest since any feedback
# patch that is the longest open
