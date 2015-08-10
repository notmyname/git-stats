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





patches = defaultdict(list)
count = 0
biggest = 0
big = None
for patches_input in sys.argv[1:]:
    with open(patches_input) as f:
        for line in f:
            parsed = json.loads(line)
            try:
                if parsed['id'] in ('I755b62bb4d0110211a38db2af010178d8ae7aa09', # spurious comment on abandoned patch
                                    'I54d54eb8984d6bca4be912e7451f82e11b2db6ca', # db backends
                                    'Ia86f8b9b8886cc53ab6bb58cf117fe4c8d2a3903', # container acl headers
                                    'I45748c9d3907b9e50cd7a70047d669cb36dac526', # containeralias middleware
                                    'I3c82f8c0e7eafa3fcfc4385c9a240b14bc766ead', # data mingration
                                   ):
                    continue
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
                    big = (parsed['subject'], parsed['id'])
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
