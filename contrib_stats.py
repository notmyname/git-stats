import json
import subprocess
import datetime
import re

from matplotlib import pyplot

# TODO: track contributor half-life
# TODO: derivative of totals
# TODO: figure out churn
# TODO: how long do patches stay in review (first proposal to merge time)

chunk_size = 30  # number of days for one "chunk" of time

def timeblock_iter():
    start = 0
    end = start + chunk_size
    while True:
        yield (start, end)
        start += 7
        end += 7

def get_max_days_ago():
    oldest_date = subprocess.check_output(
        'git log --reverse --format="%ad" --date=short | head -1', shell=True)
    oldest_date = oldest_date.strip()
    date = datetime.datetime.strptime(oldest_date, '%Y-%m-%d')
    delta = datetime.datetime.now() - date
    return delta.days

def get_one_day(days_ago):
    cmd = ("git shortlog -es --no-merges --before='@{%d days ago}' "
            "--since='@{%d days ago}'" % (days_ago - 1, days_ago))
    out = subprocess.check_output(cmd, shell=True).strip()
    authors = set()
    for line in out.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r'\d+\s+(.*)', line)
            authors.add(match.group(1))
    return authors

def get_data():
    '''
    returns a list of sets. the first element is the list of committers from the
    first commit to the repo, and the last element is the list of committers from
    yesterday.
    '''
    max_days = get_max_days_ago()
    max_days = 30
    data = []
    while max_days >= 0:
        authors_for_day = get_one_day(max_days)
        data.append(authors_for_day)
        max_days -= 1
    return data

def make_graph(d):
    d.reverse()
    while d[0][1] == 0:
        d.pop(0)
    change_in_cumulative = []
    change_in_period = []
    starts = []
    values = []
    last_count = 0
    last_total = 0
    for start, count, total in d:
        starts.append(start)
        values.append(count)
        change_in_cumulative.append(total - last_total)
        change_in_period.append(count - last_count)
        last_count = count
        last_total = total
    totals = [x[2] for x in d]
    pyplot.plot(starts, values, '-', color='blue', label="Contribs in period")  #, drawstyle='steps')
    #pyplot.plot(starts, totals, '-', color='red', label="Total")
    pyplot.plot(starts, change_in_cumulative, '-', color='green', label="Totals rate of change")
    pyplot.plot(starts, change_in_period, '-', color='black', label="Period rate of change")
    pyplot.title('Active contributors')
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('active_contribs.png', bbox_inches='tight', pad_inches=0.25)

filename = 'contrib_stats.data'

try:
    with open(filename, 'rb') as f:
        raw_data = [set(e) for e in json.load(f)]
except (IOError, ValueError):
    raw_data = get_data()
    with open(filename, 'wb') as f:
        json.dump([list(e) for e in raw_data], f)

make_graph(raw_data)
