import json
import subprocess
import datetime
import re
import operator

from numpy import arange
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

def get_min_days_ago():
    newest_date = subprocess.check_output(
        'git log --format="%ad" --date=short | head -1', shell=True)
    newest_date = newest_date.strip()
    date = datetime.datetime.strptime(newest_date, '%Y-%m-%d')
    delta = datetime.datetime.now() - date
    return delta.days

MAX_DAYS_AGO = get_max_days_ago()
MIN_DAYS_AGO = get_min_days_ago()
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
            author = author.decode('utf8')
            if author not in excluded_authors:
                authors.add(author)
    return authors

def get_data(max_days, min_days):
    '''
    returns a list of sets. the first element is the list of committers from the
    first commit to the repo, and the last element is the list of committers from
    yesterday.
    '''
    data = []
    while max_days >= 0:
        if max_days <= min_days:
            print 'No newer data in VCS'
            break
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

def make_one_range_plot_values(all_ranges, yval, all_x_vals):
    new_x_vals = []
    for x_val in all_x_vals:
        for run in all_ranges:
            if x_val in range(min(run), max(run)):
                new_x_vals.append(yval)
                break
        else:
            new_x_vals.append(None)
    return new_x_vals

def make_graph(contribs_by_days_ago):
    all_contribs = set()
    totals = []
    actives = []
    dtotal = []
    dactive = []
    active_window = 30  # number of days a contributor stays "active"
    contributor_activity = {}  # contrib -> [(start_date, end_date), ...]
    contrib_activity_days = {}
    rs = RollingSet(active_window)
    for date, c in contribs_by_days_ago:
        end_window = datetime.datetime.strptime(date, '%Y-%m-%d') + \
            datetime.timedelta(days=active_window)
        end_window_days = (datetime.datetime.now() - end_window).days
        start_date_days = (datetime.datetime.now() -
                           datetime.datetime.strptime(date, '%Y-%m-%d')).days
        date = str(date)
        end_window = str(end_window.strftime('%Y-%m-%d'))
        for person in c:
            if person not in contributor_activity:
                contributor_activity[person] = [(date, end_window)]
                contrib_activity_days[person] = [(start_date_days,
                                                  end_window_days)]
            else:
                last_range = contributor_activity[person][-1]
                if datetime.datetime.strptime(date, '%Y-%m-%d') < \
                        datetime.datetime.strptime(last_range[1], '%Y-%m-%d'):
                    # we're still in the person's current active range
                    new_range = (last_range[0], end_window)
                    new_range_days = (contrib_activity_days[person][-1][0],
                                      end_window_days)
                    contributor_activity[person].pop()
                    contrib_activity_days[person].pop()
                else:
                    # old range ended, make a new one
                    new_range = (date, end_window)
                    new_range_days = (start_date_days, end_window_days)
                contributor_activity[person].append(new_range)
                contrib_activity_days[person].append(new_range_days)
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

    # find the people with the longest continuous contrib run
    max_contrib_runs = []
    for person, date_ranges in contributor_activity.items():
        line_out = [person.encode('utf8')]
        for s, e in date_ranges:
            line_out.append('%s %s' % (s, e))
        # print ','.join(line_out)
        max_run = 0
        max_run_stop_date = None
        for run in date_ranges:
            contrib_run = (
                datetime.datetime.strptime(run[1], '%Y-%m-%d') -
                datetime.datetime.strptime(run[0], '%Y-%m-%d')).days
            if contrib_run > max_run:
                max_run = contrib_run
                max_run_stop_date = run[1]
        max_contrib_runs.append((max_run, person, max_run_stop_date))
    max_contrib_runs.sort(reverse=True)
    # print '\n'.join('%s: %s (%s)' % (p, c, d) for (c, p, d) in max_contrib_runs[:10])


    # get graphable ranges for each person
    graphable_ranges = {}
    total_x_values = range(MAX_DAYS_AGO, MIN_DAYS_AGO-active_window, -1)
    for person, days_ago_ranges in contrib_activity_days.items():
        # if person not in [x[1] for x in max_contrib_runs[:50]]:
            # continue
        yval = len(graphable_ranges)
        new_data = make_one_range_plot_values(days_ago_ranges, yval,
                                              total_x_values)
        graphable_ranges[person] = (yval, new_data)

    xs = range(MAX_DAYS_AGO, MIN_DAYS_AGO, -1)

    lens = map(len, [totals, actives, dtotal, dactive, xs])
    assert len(set(lens)) == 1, lens

    title_date = (datetime.datetime.now() - datetime.timedelta(days=MIN_DAYS_AGO)).date()
    lookback = MAX_DAYS_AGO
    pyplot.plot(xs[-lookback:], actives[-lookback:], '-', color='blue',
                label="Active contributors", drawstyle="steps")
    pyplot.title('Active contributors (as of %s)' % title_date)
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
    pyplot.title('Total contributors (as of %s)' % title_date)
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
    pyplot.title('Change in contributors over time (as of %s)' % title_date)
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
    pyplot.close()

    lookback = MAX_DAYS_AGO
    xs = range(MAX_DAYS_AGO, MIN_DAYS_AGO-active_window, -1)
    persons = []
    for person, (i, person_days) in graphable_ranges.items():
        persons.append((i, person.split('<', 1)[0].strip()))
        pyplot.plot(xs, person_days, '-',
                    label=person, linewidth=10, solid_capstyle="butt", alpha=0.6)
    pyplot.title('Contributor Actvity (as of %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributor')
    persons.sort()
    pyplot.yticks([p[0] for p in persons], [p[1] for p in persons]) # rotation=45
    pyplot.autoscale(enable=True, axis='both', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(32, 50)
    fig.dpi = 200
    fig.set_frameon(False)
    fig.savefig('contrib_activity.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

try:
    raw_data = load(FILENAME)
    # update the data first
    most_recent_date = raw_data[-1][0]
    days_ago = (datetime.datetime.now() - \
        datetime.datetime.strptime(most_recent_date, '%Y-%m-%d')).days - 1
    if days_ago < MIN_DAYS_AGO:  ## is this right?
        print 'Updating previous data with %d days...' % days_ago
        recent_data = get_data(days_ago, MIN_DAYS_AGO)
        raw_data.extend(recent_data)
        save(raw_data, FILENAME)
    else:
        print 'Data file (%s) is up to date.' % FILENAME
except (IOError, ValueError):
    raw_data = get_data(MAX_DAYS_AGO, MIN_DAYS_AGO)
    save(raw_data, FILENAME)

make_graph(raw_data)
