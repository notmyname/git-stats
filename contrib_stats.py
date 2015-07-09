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
# TODO: how long do patches stay in review (first proposal to merge time)
# TODO: find how many one-off contributors we can support in one time block (map to review time?)

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
    'OpenStack Jenkins <jenkins@openstack.org>',
)

def get_one_day(days_ago):
    cmd = ("git shortlog -es --before='@{%d days ago}' "
            "--since='@{%d days ago}'" % (days_ago - 1, days_ago))
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

def get_data(max_days, min_days):
    '''
    returns a list of sets. the first element is the list of committers from the
    first commit to the repo, and the last element is the list of committers from
    yesterday.
    '''
    data = []
    authors_by_count = defaultdict(int)
    while max_days >= 0:
        if max_days <= min_days:
            print 'No newer data in VCS'
            break
        that_date = datetime.datetime.now() - datetime.timedelta(days=max_days)
        that_date = that_date.strftime('%Y-%m-%d')
        authors_for_day, by_count = get_one_day(max_days)
        for a, c in by_count.items():
            authors_by_count[a] += c
        data.append((that_date, authors_for_day))
        max_days -= 1
        if max_days % 20 == 0:
            print '%d days left...' % max_days
    return data, authors_by_count

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


def save(contribs_by_days_ago, authors_by_count, filename):
    listified = [(d, list(e)) for (d, e) in contribs_by_days_ago]
    with open(filename, 'wb') as f:
        json.dump((listified, authors_by_count), f)

def load(filename):
    with open(filename, 'rb') as f:
        (listified, authors_by_count) = json.load(f)
    contribs_by_days_ago = [(d, set(e)) for (d, e) in listified]
    return contribs_by_days_ago, authors_by_count

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

def make_graph(contribs_by_days_ago, authors_by_count, active_window=14):
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
    single_contrib_count_by_bucket = defaultdict(int)
    total_contrib_count_by_bucket = defaultdict(int)
    bucket_size = 60
    total_x_values = range(MAX_DAYS_AGO, MIN_DAYS_AGO-active_window, -1)
    total_age = total_x_values[0] - total_x_values[-1]
    for person, days_ago_ranges in contrib_activity_days.items():
        new_data = make_one_range_plot_values(days_ago_ranges, 1,
                                              total_x_values)
        start_day = new_data.index(1)
        count = new_data.count(1)
        if authors_by_count[person] == 1:
            single_contrib_count_by_bucket[(total_age - start_day) // bucket_size] += 1
        total_contrib_count_by_bucket[(total_age - start_day) // bucket_size] += 1
        order.append((start_day, person))
        # find who's at risk of falling out
        last_days_ago = days_ago_ranges[-1][-1]
        r = count / float(authors_by_count[person])
        # at least one patch, active in the last 90 days, and it's been longer than normal since your last patch
        if last_days_ago > r and authors_by_count[person] > 1 and last_days_ago < 180:
            m = '%s: last: %s (total days active: %s, avg days per patch: %.2f)' % (person, last_days_ago, count, r)
            print m
    # this needs work. it should count someone as one-time if they've only landed one patch up to that bucket point
    # print "Number of one-time contributors in a time bucket"
    # for b in total_contrib_count_by_bucket:
    #     ratio = single_contrib_count_by_bucket[b] / float(total_contrib_count_by_bucket[b])
    #     print '%d: %d, %d, %.2f' % (b*bucket_size, total_contrib_count_by_bucket[b], single_contrib_count_by_bucket[b], ratio)
    order.sort(reverse=True)
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
        how_many_days = person_days.count(i)
        c = authors_by_count[person]
        r = how_many_days / float(c)
        persons.append((i, person.split('<', 1)[0].strip() + ' (%d, %.2f)' % (c, r)))
        alpha = 1.0
        if authors_by_count[person] == 1:
            alpha = 0.5
        days_since_first = total_age - person_days.index(i)
        # since your first commit, how much of the life of the project have you been active?
        rcolor = int((how_many_days / float(days_since_first)) * 0xff) - 1

        bcolor = 0x7f
        # how much of the total life of the project have you been active?
        gcolor = 0  # int((how_many_days / float(total_age)) * 0xff) - 1
        pyplot.plot(total_x_values, person_days, '-',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=alpha, color='#%.2x%.2x%.2x' % (rcolor, gcolor, bcolor))
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
        contribs_by_days_ago, authors_by_count = load(FILENAME)
        # update the data first
        most_recent_date = max(x[0] for x in contribs_by_days_ago)
        days_ago = (datetime.datetime.now() - \
            datetime.datetime.strptime(most_recent_date, '%Y-%m-%d')).days - 1
        if days_ago > MIN_DAYS_AGO:
            print 'Updating previous data with %d days...' % days_ago
            recent_data = get_data(days_ago, MIN_DAYS_AGO)
            contribs_by_days_ago.extend(recent_data)
            save(contribs_by_days_ago, authors_by_count, FILENAME)
        else:
            print 'Data file (%s) is up to date.' % FILENAME
    except (IOError, ValueError):
        contribs_by_days_ago, authors_by_count = get_data(MAX_DAYS_AGO, MIN_DAYS_AGO)
        save(contribs_by_days_ago, authors_by_count, FILENAME)

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
    make_graph(contribs_by_days_ago, authors_by_count, aw)
