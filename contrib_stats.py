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

MAX_DAYS_AGO = get_max_days_ago()
FILENAME = 'contrib_stats.data'

excluded_authors = (
    'Jenkins <jenkins@review.openstack.org>',
    'OpenStack Proposal Bot <openstack-infra@lists.openstack.org>',
)

def get_one_day(days_ago):
    cmd = ("git shortlog -es --before='@{%d days ago}' "
            "--since='@{%d days ago}'" % (days_ago - 1, days_ago))
    out = subprocess.check_output(cmd, shell=True).strip()
    authors = set()
    for line in out.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r'\d+\s+(.*)', line)
            author = match.group(1)
            if author not in excluded_authors:
                authors.add(author)
    return authors

def get_data(max_days):
    '''
    returns a list of sets. the first element is the list of committers from the
    first commit to the repo, and the last element is the list of committers from
    yesterday.
    '''
    data = []
    while max_days >= 0:
        that_date = datetime.datetime.now() - datetime.timedelta(days=max_days)
        that_date = that_date.strftime('%Y-%m-%d')
        authors_for_day = get_one_day(max_days)
        data.append((that_date, authors_for_day))
        max_days -= 1
        if max_days % 20 == 0:
            print '%d days left...' % max_days
    return data

class WindowQueue(object):
    def __init__(self, window_size):
        self.q = []
        self.window_size = window_size

    def add(self, o):
        if len(self.q) > self.window_size:
            raise Exception('oops')
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


def save(raw_data, filename):
    with open(filename, 'wb') as f:
        json.dump([(d, list(e)) for (d, e) in raw_data], f)

def load(filename):
    with open(filename, 'rb') as f:
        raw_data = [(d, set(e)) for (d, e) in json.load(f)]
    return raw_data

def make_graph(contribs_by_days_ago):
    all_contribs = set()
    totals = []
    actives = []
    dtotal = []
    dactive = []
    active_set_of_contribs = set()
    count_by_contribs = {}
    for date, c in contribs_by_days_ago:
        for contrib in c:
            count = count_by_contribs.get(contrib, 0)
            count_by_contribs[contrib] = count + 1
    for contrib, count in count_by_contribs.items():
        if count > 1:  # exclude people with this many or less commits
            active_set_of_contribs.add(contrib)
    rs = RollingSet(30)  # number of days a contributor stays "active"
    for date, c in contribs_by_days_ago:
        for person in c.copy():
            if person not in active_set_of_contribs:
                c.remove(person)
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


    days_ago = len(contribs_by_days_ago) - 1
    xs = range(days_ago, -1, -1)

    lens = map(len, [totals, actives, dtotal, dactive, xs])
    assert len(set(lens)) == 1, lens

    title_date = datetime.datetime.now().date()
    lookback = days_ago
    pyplot.plot(xs[-lookback:], actives[-lookback:], '-', color='blue',
                label="Active contributors", drawstyle="steps")
    pyplot.title('Active contributors (on %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('active_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    pyplot.plot(xs[-lookback:], totals[-lookback:], '-', color='red',
               label="Total contributors", drawstyle="steps")
    pyplot.title('Total contributors (on %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('total_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    lookback = 365
    pyplot.plot(xs[-lookback:], dactive[-lookback:], '-',
                color='blue', label="Active contributors", drawstyle="steps")
    pyplot.plot(xs[-lookback:], dtotal[-lookback:], '-',
                color='red', label="Total contributors", drawstyle="steps")
    pyplot.title('Change in contributors over time (on %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Change in contributors')
    pyplot.legend(loc='upper left')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('contrib_deltas.png', bbox_inches='tight', pad_inches=0.25)

try:
    raw_data = load(FILENAME)
    # update the data first
    most_recent_date = raw_data[-1][0]
    days_ago = (datetime.datetime.now() - \
        datetime.datetime.strptime(most_recent_date, '%Y-%m-%d')).days - 1
    if days_ago > 0:
        print 'Updating previous data with %d days...' % days_ago
        recent_data = get_data(days_ago)
        raw_data.extend(recent_data)
        save(raw_data, FILENAME)
    else:
        print 'Data file (%s) is up to date.' % FILENAME
except (IOError, ValueError):
    raw_data = get_data(MAX_DAYS_AGO)
    save(raw_data, FILENAME)

make_graph(raw_data)
