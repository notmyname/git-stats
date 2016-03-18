#!/usr/bin/env python

'''
parse the output of
`git rev-list --pretty=format:"%aN|<%aE>|%aI" HEAD | grep -v commit`
into a dictionary and dump as json
'''

import sys
import dateutil.parser
import collections
import json
import datetime

from utils import map_one_person, date_range, COMMITS_FILENAME, \
    excluded_authors


def load_commits():
    with open(COMMITS_FILENAME, 'rb') as f:
        (contribs_by_date, authors_by_count) = json.load(f)
    return contribs_by_date, authors_by_count


def save_commits(data):
    with open(COMMITS_FILENAME, 'wb') as f:
        json.dump(data, f)

if __name__ == '__main__':
    people_by_date = collections.defaultdict(list)
    dates_by_person = collections.defaultdict(list)
    for line in sys.stdin.readlines():
        if not line.strip():
            continue
        name, email, timestamp = line.strip().split('|')
        person = ('%s %s' % (name, email)).decode('utf8')
        person = '%s %s' % (map_one_person(person), email)
        if person.lower() in excluded_authors:
            continue
        ts = dateutil.parser.parse(timestamp).strftime('%Y-%m-%d')
        people_by_date[ts].append(person)
        dates_by_person[person].append(ts)

    # fill in any missing days
    first_date = min(people_by_date.keys())
    for day in date_range(first_date, datetime.datetime.now()):
        if day not in people_by_date:
            people_by_date[day] = []

    save_commits((people_by_date, dates_by_person))
