import json
import subprocess
import datetime
import re
import operator
import sys
from collections import defaultdict

from numpy import arange
from matplotlib import pyplot

# TODO: track contributor half-life
# TODO: derivative of totals
# TODO: figure out churn
# TODO: how long do patches stay in review (first proposal to merge time)

# TODO: rolling average for active count graph
# TODO: (1) total active time (2) histogram of total active time

def get_max_min_days_ago():
    all_dates = subprocess.check_output(
        'git log --reverse --format="%ad" --date=short', shell=True)
    now = datetime.datetime.now()
    oldest_date = now
    newest_date = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')
    for date in all_dates.split():
        date = datetime.datetime.strptime(date.strip(), '%Y-%m-%d')
        if date < oldest_date:
            oldest_date = date
        elif date > newest_date:
            newest_date = date
    oldest = now - oldest_date
    newest = now - newest_date
    return oldest.days, newest.days

MAX_DAYS_AGO, MIN_DAYS_AGO = get_max_min_days_ago()
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
    global_start = min(x[1] for x in all_ranges)
    global_end = max(x[0] for x in all_ranges)
    global_range = range(global_start, global_end)
    for x_val in all_x_vals:
        # for run in all_ranges:
        #     if x_val in range(min(run), max(run)):
        #         new_x_vals.append(yval)
        #         break
        if x_val in global_range:
            new_x_vals.append(yval)
        else:
            new_x_vals.append(None)
    return new_x_vals

def make_graph(contribs_by_days_ago, active_window=14):
    all_contribs = set()
    totals = []
    actives = []
    actives_avg = []
    rolling_avg_window = 90
    dtotal = []
    dactive = []
    contributor_activity = {}  # contrib -> [(start_date, end_date), ...]
    contrib_activity_days = {}  # contrib -> [(start_days_ago, end_days_ago), ...]
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
        denom = min(len(actives), rolling_avg_window)
        s = sum(actives[-rolling_avg_window:])
        actives_avg.append(float(s) / denom)
        try:
            dtotal.append(totals[-1] - totals[-2])
            dactive.append(actives[-1] - actives[-2])
        except:
            dtotal.append(0)
            dactive.append(0)

    # get graphable ranges for each person
    graphable_ranges = {}
    order = []
    total_x_values = range(MAX_DAYS_AGO, MIN_DAYS_AGO-active_window, -1)
    for person, days_ago_ranges in contrib_activity_days.items():
        new_data = make_one_range_plot_values(days_ago_ranges, 1,
                                              total_x_values)
        order.append((new_data, person))
        # find who's at risk of falling out
        count = new_data.count(1)
        last_days_ago = days_ago_ranges[-1][-1]
        if 30 <= last_days_ago < 180 and count > active_window:
            m = '%s: last: %s (total days active: %s)' % (person, last_days_ago, count)
            print m
    order.sort()
    for _junk, person in order:
        days_ago_ranges = contrib_activity_days[person]
        yval = len(graphable_ranges)
        new_data = make_one_range_plot_values(days_ago_ranges, yval,
                                              total_x_values)
        graphable_ranges[person] = (yval, new_data)

    xs = range(MAX_DAYS_AGO, MIN_DAYS_AGO, -1)

    lens = map(len, [totals, actives, actives_avg, dtotal, dactive, xs])
    assert len(set(lens)) == 1, lens

    title_date = (datetime.datetime.now() - datetime.timedelta(days=MIN_DAYS_AGO)).date()

    # graph active contribs
    lookback = MAX_DAYS_AGO
    pyplot.plot(xs[-lookback:], actives[-lookback:], '-', color='blue',
                label="Active contributors", drawstyle="steps")
    pyplot.plot(xs[-lookback:], actives_avg[-lookback:], '-', color='red',
                label="Active contributors (%d day avg)" % rolling_avg_window,
                drawstyle="steps")
    pyplot.title('Active contributors (as of %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    x_ticks = range(0, MAX_DAYS_AGO, 90)
    pyplot.xticks(x_ticks, x_ticks)
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('active_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # graph total contributors
    pyplot.plot(xs[-lookback:], totals[-lookback:], '-', color='red',
               label="Total contributors", drawstyle="steps")
    pyplot.title('Total contributors (as of %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    x_ticks = range(0, MAX_DAYS_AGO, 90)
    pyplot.xticks(x_ticks, x_ticks)
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('total_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # graph deltas
    lookback = 365
    pyplot.plot(xs[-lookback:], dactive[-lookback:], '-',
                color='blue', label="Active contributors", drawstyle="steps")
    pyplot.plot(xs[-lookback:], dtotal[-lookback:], '-',
                color='red', label="Total contributors", drawstyle="steps")
    pyplot.title('Change in contributors over time (as of %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Change in contributors')
    pyplot.legend(loc='upper left')
    x_ticks = range(0, lookback, 30)
    pyplot.xticks(x_ticks, x_ticks)
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('contrib_deltas.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # graph contrib activity ranges
    persons = []
    for person, (i, person_days) in graphable_ranges.items():
        persons.append((i, person.split('<', 1)[0].strip()))
        alpha = 1.0
        foo = int((person_days.count(i) / float(active_window)) * 100)
        if foo == 100:
            alpha = 0.25
        pyplot.plot(total_x_values, person_days, '-',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=alpha)
    pyplot.title('Contributor Actvity (as of %s)' % title_date)
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributor')
    persons.sort()
    pyplot.yticks([p[0] for p in persons], [p[1] for p in persons])
    x_ticks = range(0, MAX_DAYS_AGO, 60)
    pyplot.xticks(x_ticks, x_ticks)
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.ylim(-1, persons[-1][0] + 1)
    pyplot.autoscale(enable=True, axis='x', tight=True)
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.dpi = 200
    vertical_size_per_person = 0.25
    vertical_size = vertical_size_per_person * len(persons)
    horizontal_size_per_day = 0.02
    horizontal_size = horizontal_size_per_day * len(total_x_values)
    fig.set_size_inches(horizontal_size, vertical_size)
    fig.set_frameon(False)
    fig.savefig('contrib_activity.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()


if __name__ == '__main__':
    try:
        raw_data = load(FILENAME)
        # update the data first
        most_recent_date = max(x[0] for x in raw_data)
        days_ago = (datetime.datetime.now() - \
            datetime.datetime.strptime(most_recent_date, '%Y-%m-%d')).days - 1
        if days_ago > MIN_DAYS_AGO:
            print 'Updating previous data with %d days...' % days_ago
            recent_data = get_data(days_ago, MIN_DAYS_AGO)
            raw_data.extend(recent_data)
            save(raw_data, FILENAME)
        else:
            print 'Data file (%s) is up to date.' % FILENAME
    except (IOError, ValueError):
        raw_data = get_data(MAX_DAYS_AGO, MIN_DAYS_AGO)
        save(raw_data, FILENAME)

    aw = 14
    try:
        aw = sys.argv[1]
        try:
            aw = int(aw)
        except ValueError:
            print 'bad active window given (%s). defaulting to 14' % aw
    except IndexError:
        aw = 14

    print 'Using activity window of %d' % aw
    make_graph(raw_data, aw)  
