import sys
import datetime
import subprocess
from collections import defaultdict
import json
import re

def date_range(start_date, end_date, strings=True):
    '''yields an inclusive list of dates'''
    step = datetime.timedelta(days=1)
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    while start_date <= end_date:
        if strings:
            yield start_date.strftime('%Y-%m-%d')
        else:
            yield start_date
        start_date += step

def get_max_min_days_ago():
    '''returns the first and last dates of activity in a repo'''
    all_dates = subprocess.check_output(
        'git log --reverse --format="%ad" --date=short', shell=True)
    oldest_date = datetime.datetime.now()
    newest_date = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')
    for date in all_dates.split():
        date = datetime.datetime.strptime(date.strip(), '%Y-%m-%d')
        if date < oldest_date:
            oldest_date = date
        elif date > newest_date:
            newest_date = date
    return oldest_date.date(), newest_date.date()

FIRST_DATE, LAST_DATE = get_max_min_days_ago()
FILENAME = 'contrib_stats2.data'
REVIEWS_FILENAME = 'swift_gerrit_history.patches'

excluded_authors = (
    'Jenkins <jenkins@review.openstack.org>',
    'OpenStack Proposal Bot <openstack-infra@lists.openstack.org>',
    'OpenStack Jenkins <jenkins@openstack.org>',
    'SwiftStack Cluster CI <openstack-ci@swiftstack.com>',
    'Rackspace GolangSwift CI <mike+goci@weirdlooking.com>',
    'Trivial Rebase <trivial-rebase@review.openstack.org>',
    'Coraid CI <coraid-openstack-ci-all@mirantis.com>',
)

def save_commits(contribs_by_days_ago, authors_by_count, filename):
    listified = [(d, list(e)) for (d, e) in contribs_by_days_ago]
    with open(filename, 'wb') as f:
        json.dump((listified, authors_by_count), f)

def load_commits(filename):
    with open(filename, 'rb') as f:
        (listified, authors_by_count) = json.load(f)
    contribs_by_days_ago = [(d, set(e)) for (d, e) in listified]
    return contribs_by_days_ago, authors_by_count

def get_one_day(date):
    next_day = date + datetime.timedelta(days=1)
    cmd = ("git shortlog -es --since='@{%s}' --before='@{%s}'"
           % (date.strftime('%Y-%m-%d'),
              next_day.strftime('%Y-%m-%d')))
    out = subprocess.check_output(cmd, shell=True).strip()
    authors = set()
    authors_by_count = defaultdict(int)
    for line in out.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r'\d+\s+(.*)', line)
            author = match.group(1)
            author = author.decode('utf8')
            if author not in excluded_authors:
                authors.add(author)
            authors_by_count[author] += 1
    return authors, authors_by_count

def get_data(start_date, end_date):
    data = []
    authors_by_count = defaultdict(int)
    for date in date_range(start_date, end_date, strings=False):
        authors_for_day, by_count = get_one_day(date)
        for a, c in by_count.items():
            authors_by_count[a] += c
        data.append((date.strftime('%Y-%m-%d'), authors_for_day))
        print date  # how do I print only every 20 days?
    return data, authors_by_count

if __name__ == '__main__':
    # load patch info
    try:
        contribs_by_days_ago, authors_by_count = load_commits(FILENAME)
        # update the data first
        most_recent_date = max(x[0] for x in contribs_by_days_ago)
        most_recent_date = datetime.datetime.strptime(
            most_recent_date, '%Y-%m-%d').date()
        print 'Last date found in data file:', most_recent_date
        print 'Last date found in source repo:', LAST_DATE
        if most_recent_date < LAST_DATE:
            print 'Updating previous data with data since %s...' % most_recent_date
            recent_data, new_by_count = get_data(most_recent_date, LAST_DATE)
            contribs_by_days_ago.extend(recent_data)
            for a, c in new_by_count.items():
                if a not in authors_by_count:
                    authors_by_count[a] = 0
                authors_by_count[a] += c
            save_commits(contribs_by_days_ago, authors_by_count, FILENAME)
        else:
            print 'Data file (%s) is up to date.' % FILENAME
    except (IOError, ValueError):
        contribs_by_days_ago, authors_by_count = get_data(FIRST_DATE, LAST_DATE)
        save_commits(contribs_by_days_ago, authors_by_count, FILENAME)
    sorted_authors = sorted(authors_by_count.keys())
    for a in sorted_authors:
        print a, authors_by_count[a]
    # load review info
    # combine data sources down to one set of "contributors"
    # draw graphs
