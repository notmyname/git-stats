import json
import subprocess
import time
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


def save_commits(contribs_by_days_ago, authors_by_count, filename):
    listified = [(d, list(e)) for (d, e) in contribs_by_days_ago]
    with open(filename, 'wb') as f:
        json.dump((listified, authors_by_count), f)

def load_commits(filename):
    with open(filename, 'rb') as f:
        (listified, authors_by_count) = json.load(f)
    contribs_by_days_ago = [(d, set(e)) for (d, e) in listified]
    return contribs_by_days_ago, authors_by_count


# returns {unmapped person: mapped name email}
def make_mapping():
    mapped_people = {}
    mailmap = {}
    with open('.mailmap', 'rb') as f:
        for line in f:
            line = line.strip()
            name_email, rest = line.split('>', 1)
            name, email = name_email.rsplit(' ', 1)
            email = email + '>'
            real = '%s %s' % (name, email)
            rest = rest.strip()
            if '<' in rest:
                rest = rest[rest.index('<'):]
            else:
                rest = email
            mapped_people[rest] = real
    return mapped_people


def load_reviewers(filename):
    reviewers = defaultdict(set)
    mapping = make_mapping()
    with open(filename, 'rb') as f:
        for line in f:
            if line:
                review_data = json.loads(line)
            else:
                continue
            if 'comments' not in review_data:
                continue
            for review_comment in review_data['comments']:
                when = review_comment['timestamp']
                days_ago = datetime.timedelta(seconds=time.time() - when).days
                reviewer = review_comment['reviewer']
                if 'email' not in reviewer:
                    continue
                email = '<%s>' % reviewer['email']
                name_email = '%s %s' % (reviewer['name'], email)
                if email in mapping:
                    name_email = mapping[email]
                if name_email not in excluded_authors:
                    reviewers[name_email].add(days_ago)
    return reviewers

def make_one_range_plot_values(all_ranges, yval, all_x_vals, review_dates):
    global_start = 9999999999
    global_end = -global_start
    if all_ranges is not None:
        global_start = min(x[1] for x in all_ranges)
        global_end = max(x[0] for x in all_ranges)
    if review_dates is not None:
        first_review = min(review_dates)
        last_review = max(review_dates)
        if first_review == last_review:
            last_review += 1
        global_start = min(global_start, first_review)
        global_end = max(global_end, last_review)
    global_range = range(global_start, global_end)
    cumulative_x_vals = [None] * len(all_x_vals)
    sparse_x_vals = [None] * len(all_x_vals)
    review_x_vals = [None] * len(all_x_vals)
    for i, x_val in enumerate(all_x_vals):
        if all_ranges:
            for run in all_ranges:
                if x_val in range(min(run), max(run)):
                    sparse_x_vals[i] = yval
                    break
        if x_val in global_range:
            cumulative_x_vals[i] = yval
        if review_dates:
            if x_val in review_dates:
                review_x_vals[i] = yval
                review_x_vals[i+1] = yval
    return cumulative_x_vals, sparse_x_vals, review_x_vals


def make_graph(contribs_by_days_ago, authors_by_count, reviewers,
               active_window=14):
    all_contribs = set()
    totals = []
    actives_windows = [(180, (365, 730)), (90, (180, 365)), (14, (30, 90))]
    actives = {x: [] for (x, _) in actives_windows}
    rolling_sets = {x: RollingSet(x) for (x, _) in actives_windows}
    actives_avg = {x: defaultdict(list) for (x, _) in actives_windows}
    dtotal = []
    dactive = []
    contributor_activity = {}  # contrib -> [(start_date, end_date), ...]
    contrib_activity_days = {}  # contrib -> [(start_days_ago, end_days_ago), ...]
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
        for aw, rolling_avg_windows in actives_windows:
            rolling_sets[aw].add(c)
            actives[aw].append(len(rolling_sets[aw]))
            for r_a_w in rolling_avg_windows:
                denom = min(len(actives[aw]), r_a_w)
                s = sum(actives[aw][-r_a_w:])
                actives_avg[aw][r_a_w].append(float(s) / denom)

    # get graphable ranges for each person
    graphable_ranges = {}
    order = []
    bucket_size = 60
    total_x_values = range(MAX_DAYS_AGO, MIN_DAYS_AGO-active_window, -1)
    total_age = total_x_values[0] - total_x_values[-1]
    total_people = set(contrib_activity_days.keys() + reviewers.keys())
    for person in total_people:
        days_ago_ranges = contrib_activity_days.get(person)
        cumulative_x_vals, sparse_x_vals, review_x_vals = \
            make_one_range_plot_values(
                days_ago_ranges, 1, total_x_values, reviewers.get(person))
        start_day = cumulative_x_vals.index(1)
        count = sparse_x_vals.count(1)
        danger_metric = 0.0
        # find who's at risk of falling out (need to update for reviewers)
        if count:
            last_days_ago = days_ago_ranges[-1][-1]
            avg_days_active_per_patch = count / float(authors_by_count[person])
            danger_metric = last_days_ago / avg_days_active_per_patch
            # at least one patch, active in the last 90 days, and it's been longer
            # than normal since your last patch
            if authors_by_count[person] > 1 and 1.5 < danger_metric < 5.0:
                m = ('%s:\n\tlast active %s days ago (patches: %d, '
                     'total days active: %s, avg activity per patch: %.2f, '
                     'danger: %.2f)'
                    ) % (person, last_days_ago, authors_by_count[person], count,
                         avg_days_active_per_patch, danger_metric)
                print m
        order.append((start_day, danger_metric, person))
    order.sort(reverse=True)
    for _junk, danger_metric, person in order:
        days_ago_ranges = contrib_activity_days.get(person)
        yval = len(graphable_ranges)
        cumulative_x_vals, sparse_x_vals, review_x_vals = \
            make_one_range_plot_values(
                days_ago_ranges, yval, total_x_values, reviewers.get(person))
        graphable_ranges[person] = (yval, sparse_x_vals, cumulative_x_vals,
                                    danger_metric, review_x_vals)

    xs = range(MAX_DAYS_AGO, MIN_DAYS_AGO, -1)

    lens = map(len, [totals, xs])
    assert len(set(lens)) == 1, lens

    title_date = (datetime.datetime.now() - datetime.timedelta(days=MIN_DAYS_AGO)).date()

    # graph active contribs
    lookback = MAX_DAYS_AGO
    for aw, rolling_avg_windows in actives_windows:
        pyplot.plot(xs[-lookback:], actives[aw][-lookback:], '-', alpha=0.5,
                    label="%d day activity window" % aw)
        for r_a_w in rolling_avg_windows:
            pyplot.plot(xs[-lookback:], actives_avg[aw][r_a_w][-lookback:], '-',
                        label="%d day avg (%d)" % (r_a_w, aw), linewidth=3)
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
    fig.set_size_inches(24, 8)
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

    # graph contrib activity ranges
    persons = []
    for person, (i, person_days, cumulative_days, danger_metric, review_vals) in graphable_ranges.items():
        how_many_days = person_days.count(i)
        c = authors_by_count.get(person, 0)
        name = person.split('<', 1)[0].strip()
        persons.append((i, name + ' (%d, %.2f)' % (c, danger_metric)))
        days_since_first = total_age - cumulative_days.index(i)
        # since your first commit, how much of the life of the project have you been active?
        rcolor = (min(how_many_days, days_since_first) / float(days_since_first)) * 0x7f
        rcolor += 0x7f
        bcolor = 0x60
        gcolor = 0
        pyplot.plot(total_x_values, review_vals, '-',
                    label=person, linewidth=12, solid_capstyle="butt",
                    alpha=1.0, color='#006400')
        pyplot.plot(total_x_values, cumulative_days, '-',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=0.3, color='#333333')
        pyplot.plot(total_x_values, person_days, '-',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=1.0, color='#%.2x%.2x%.2x' % (rcolor, gcolor, bcolor))
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
    reviewers = load_reviewers(REVIEWS_FILENAME)
    try:
        contribs_by_days_ago, authors_by_count = load_commits(FILENAME)
        # update the data first
        most_recent_date = max(x[0] for x in contribs_by_days_ago)
        days_ago = (datetime.datetime.now() - \
            datetime.datetime.strptime(most_recent_date, '%Y-%m-%d')).days - 1
        if days_ago > MIN_DAYS_AGO:
            print 'Updating previous data with %d days...' % days_ago
            recent_data, new_by_count = get_data(days_ago, MIN_DAYS_AGO)
            contribs_by_days_ago.extend(recent_data)
            for a, c in new_by_count.items():
                if a not in authors_by_count:
                    authors_by_count[a] = 0
                authors_by_count[a] += c
            save_commits(contribs_by_days_ago, authors_by_count, FILENAME)
        else:
            print 'Data file (%s) is up to date.' % FILENAME
    except (IOError, ValueError):
        contribs_by_days_ago, authors_by_count = get_data(MAX_DAYS_AGO, MIN_DAYS_AGO)
        save_commits(contribs_by_days_ago, authors_by_count, FILENAME)

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
    make_graph(contribs_by_days_ago, authors_by_count, reviewers, aw)
