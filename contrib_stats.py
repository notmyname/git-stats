import json
import subprocess
import datetime
import re
import operator

from matplotlib import pyplot

# TODO: track contributor half-life
# TODO: derivative of totals
# TODO: figure out churn
# TODO: how long do patches stay in review (first proposal to merge time)

# separate active and total graphs
# reduce to: Are active contribs going up or down?
# do above for day, week, month, year

def get_max_days_ago():
    oldest_date = subprocess.check_output(
        'git log --reverse --format="%ad" --date=short | head -1', shell=True)
    oldest_date = oldest_date.strip()
    date = datetime.datetime.strptime(oldest_date, '%Y-%m-%d')
    delta = datetime.datetime.now() - date
    return delta.days

def get_one_day(days_ago):
    cmd = ("git shortlog -es --before='@{%d days ago}' "
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
    data = []
    while max_days >= 0:
        authors_for_day = get_one_day(max_days)
        data.append(authors_for_day)
        max_days -= 1
        if max_days % 20 == 0:
            print '%d days left...' % max_days
    return data

def contribs_in_range(contrib_lists):
    return reduce(operator.ior, contrib_lists, set())

class WindowQueue(object):
    def __init__(self, window_size):
        self.q = []
        self.window_size = window_size

    def add(self, o):
        if len(self.q) > self.window_size:
            raise Exception('I dun fucked up')
        e = None
        if len(self.q) == self.window_size:
            e = self.q.pop(0)
        self.q.append(o)
        return e

class RollingSet(object):
    def __init__(self, window_size):
        self.wq = WindowQueue(window_size)
        self.all_els = set()

    def add(self, o):
        assert isinstance(o, set)
        e = self.wq.add(o)
        if e:
            self.all_els -= e
        self.all_els |= o

    def __len__(self):
        return len(self.all_els)

def make_graph(contribs_by_days_ago):
    all_contribs = set()
    totals = []
    actives = []
    dtotal = []
    dactive = []
    rs = RollingSet(30)  # number of days a contributor stays "active"
    for c in contribs_by_days_ago:
        all_contribs |= c
        totals.append(len(all_contribs))
        rs.add(c)
        actives.append(len(rs))
        try:
            dtotal.append(totals[-1] - totals[-2])
            dactive.append(actives[-1] - actives[-2])
        except:
            dtotal.append(0)
            dactive.append(0)


    xs = range(len(contribs_by_days_ago)-1, -1, -1)

    lens = map(len, [totals, actives, dtotal, dactive, xs])
    assert len(set(lens)) == 1

    pyplot.plot(xs, actives, '-', color='blue', label="Active contributors",
                drawstyle="steps")
    #pyplot.plot(xs, totals, '-', color='red', label="Total contributors",
    #            drawstyle="steps")
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
    pyplot.close()

    lookback = 60
    pyplot.plot(xs[-lookback:], dactive[-lookback:], '-',
                color='blue', label="Active contributors", drawstyle="steps")
    pyplot.plot(xs[-lookback:], dtotal[-lookback:], '-',
                color='red', label="Total contributors", drawstyle="steps")
    pyplot.title('Change in contributors over time')
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Change in contributors')
    pyplot.legend(loc='upper left')
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('contrib_deltas.png', bbox_inches='tight', pad_inches=0.25)


filename = 'contrib_stats.data'

try:
    with open(filename, 'rb') as f:
        raw_data = [set(e) for e in json.load(f)]
except (IOError, ValueError):
    raw_data = get_data()
    with open(filename, 'wb') as f:
        json.dump([list(e) for e in raw_data], f)

make_graph(raw_data)
