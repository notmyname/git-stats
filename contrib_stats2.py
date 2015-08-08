import sys
import datetime
import subprocess
from collections import defaultdict
import json
import re
from matplotlib import pyplot


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
    'Gerrit Code Review <review@openstack.org>',
)

def save_commits(contribs_by_date, authors_by_count, filename):
    listified = [(d, list(e)) for (d, e) in contribs_by_date.items()]
    with open(filename, 'wb') as f:
        json.dump((listified, authors_by_count), f)

def load_commits(filename):
    with open(filename, 'rb') as f:
        (listified, authors_by_count) = json.load(f)
    contribs_by_date = {d: set(e) for (d, e) in listified}
    return contribs_by_date, authors_by_count

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
    data = defaultdict(set)
    authors_by_count = defaultdict(int)
    for date in date_range(start_date, end_date, strings=False):
        authors_for_day, by_count = get_one_day(date)
        for a, c in by_count.items():
            authors_by_count[a] += c
        data[date.strftime('%Y-%m-%d')].update(authors_for_day)
        print date  # how do I print only every 20 days?
    return data, authors_by_count

def load_reviewers(filename):
    reviewers_by_date = defaultdict(set)
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
                when = datetime.datetime.utcfromtimestamp(when).strftime('%Y-%m-%d')
                reviewer = review_comment['reviewer']
                if 'email' not in reviewer:
                    continue
                email = '<%s>' % reviewer['email']
                name_email = '%s %s' % (reviewer['name'], email)
                if name_email not in excluded_authors:
                    reviewers_by_date[when].add(name_email)
    return reviewers_by_date

def map_people(unmapped_people):
    mapped_people = set()
    the_people_map = {
        #'Bad Name <bad@email>': 'Good Name <good@email>'
        'gholt <z-launchpad@brim.net>': 'Greg Holt <gholt@rackspace.com>',
        'Mike Barton <mike-launchpad@weirdlooking.com>': 'Michael Barton <mike@weirdlooking.com>',
        'Chmouel Boudjnah <chmouel@enovance.com>': 'Chmouel Boudjnah <chmouel@chmouel.com>',
        'Maru Newby <mnewby@internap.com>': 'Maru Newby <marun@redhat.com>',
        'Zhongyue Luo <zhongyue.nah@intel.com>': 'Zhongyue Luo <zhongyue.luo@intel.com>',
        'James E. Blair <corvus@inaugust.com>': 'James E. Blair <jeblair@openstack.org>',
        u'Juan J. Mart\xednez <juan@memset.com>': 'Juan J. Martinez <juan@memset.com>',
        'Adrian Smith <adrian_f_smith@dell.com>': 'Adrian Smith <adrian@17od.com>',
        'Victor Rodionov <victor.rodionov@nexenta.com>': 'Victor Rodionov <victor.ordaz@gmail.com>',
        'dpdillinger <dan.dillinger@sonian.net>': 'Dan Dillinger <dan.dillinger@sonian.net>',
        'Yu.Yang <alex890714@gmail.com>': 'Alex Yang <alex890714@gmail.com>',
        'Clark Boylan <clark.boylan@gmail.com>': 'Clark Boylan <cboylan@sapwetik.org>',
        'Riqiang Li <lrqrun@gmail.com>': 'Li Riqiang <lrqrun@gmail.com>',
        'Andy McCrae <andy.mccrae@googleemail.com>': 'Andy McCrae <andy.mccrae@gmail.com>',
        'Doug Hellmann <doug.hellmann@dreamhost.com>': 'Doug Hellmann <doug@doughellmann.com>',
        'mail-zhang-yee <mail.zhang.yee@gmail.com>': 'Yee <mail.zhang.yee@gmail.com>',
        'Peter Portante <peter.a.portante@gmail.com>': 'Peter Portante <peter.portante@redhat.com>',
        'Kun Huang <gareth@unitedstack.com>': 'Kun Huang <gareth@openstacker.org>',
        'Joe Gordon <jogo@cloudscaling.com>': 'Joe Gordon <joe.gordon0@gmail.com>',
        'Edward Hope-Morley <edward.hope-morley@canonical.com>': 'Edward Hope-Morley <opentastic@gmail.com>',
        'paul luse <paul.e.luse@intel.com>': 'Paul Luse <paul.e.luse@intel.com>',
        'Newptone <xingchao@unitedstack.com>': 'Xingchao Yu <xingchao@unitedstack.com>',
        'anticw <cw@f00f.org>': 'Chris Wedgewood <cw@f00f.org>',
        'Chris Wedgwood <cw@f00f.org>': 'Chris Wedgewood <cw@f00f.org>',
        'Aaron Rosen <arosen@nicira.com>': 'Aaron Rosen <aaronorosen@gmail.com>',
        'Matthew Kassawara <mkassawara@gmail.com>': 'Matt Kassawara <mkassawara@gmail.com>',
        'Madhuri Kumari <madhuri.rai07@gmail.com>': 'Madhuri Kumari <madhuri.kumari@nectechnologies.in>',
        'James Page <james.page@canonical.com>': 'James Page <james.page@ubuntu.com>',
        'Andreas Jaeger <jaegerandi@gmail.com>': 'Andreas Jaeger <aj@suse.de>',
        'Jay S. Bryant <jsbryant@us.ibm.com>': 'Jay Bryant <jsbryant@us.ibm.com>',
        'greghaynes <greg@greghaynes.net>': 'Gregory Haynes <greg@greghaynes.net>',
        'Arnaud <arnaud.jost@ovh.net>': 'Arnaud JOST <arnaud.jost@pvh.net>',
        'Mitsuhiro SHIGEMATSU <shigematsu.mitsuhiro@lab.ntt.co.jp>': 'Mitsuhiro Shigematsu <shigematsu.mitsuhiro@lab.ntt.co.jp>',
        'MITSUHIRO Shigematsu <shigematsu.mitsuhiro@lab.ntt.co.jp>': 'Mitsuhiro Shigematsu <shigematsu.mitsuhiro@lab.ntt.co.jp>',
        'Tim Burke <tim.burke@gmail.com>': 'Tim Burke <tim@swiftstack.com>',
        'Michael MATUR <michael.matur@gmail.com>': 'Michael Matur <michael.matur@gmail.com>',
        'janonymous <jaivish.kothari@nectechnologies.in>': 'Jaivish Kothari <jaivish.kothari@nectechnologies.in>',
        'oshritf <oshritf@il.ibm.com>': 'Oshrit Feder <oshritf@il.ibm.com>',
    }
    for person in unmapped_people:
        if person in the_people_map:
            person = the_people_map[person]
        mapped_people.add(person)
    return mapped_people

def draw_contrib_activity_graph(dates_by_person, start_date, end_date):
    all_dates = list(date_range(start_date, end_date))
    x_vals = range(len(all_dates))
    graphable_data = {}
    order = []
    for person, data in dates_by_person.iteritems():
        first_day = '9999-99-99'
        last_day = '0000-00-00'
        for key in data:
            first_day = min(first_day, min(data[key]))
            last_day = max(last_day, max(data[key]))
        order.append((first_day, last_day, person))
    order.sort(reverse=True)
    for first_day, last_day, person in order:
        review_data = []
        commit_data = []
        cumulative_data = []
        sparse_cumulative_data = []
        yval = len(graphable_data)
        for date in all_dates:
            person_data = dates_by_person[person]
            active_day = False
            if date in person_data['contribs']:
                commit_data.append(yval)
                active_day = True
            else:
                commit_data.append(None)
            if date in person_data['reviews']:
                review_data.append(yval)
                active_day = True
            else:
                review_data.append(None)
            if first_day <= date <= last_day:
                cumulative_data.append(yval)
            else:
                cumulative_data.append(None)
            if active_day:
                sparse_cumulative_data.append(yval)
            else:
                sparse_cumulative_data.append(None)
        lens = map(len, [commit_data, review_data, cumulative_data, sparse_cumulative_data, x_vals])
        assert len(set(lens)) == 1, '%r %s' % (lens, person)
        graphable_data[person] = (yval, commit_data, review_data, cumulative_data, sparse_cumulative_data)

    person_labels = []
    for person, (yval, commit_data, review_data, cumulative_data, sparse_cumulative_data) in graphable_data.iteritems():
        name = person.split('<', 1)[0].strip()
        person_labels.append((yval, name))
        how_many_days_active = sparse_cumulative_data.count(yval)
        try:
            days_since_first_commit = len(x_vals) - commit_data.index(yval)
        except ValueError:
            days_since_first_commit = 0
        try:
            days_since_first_review = len(x_vals) - review_data.index(yval)
        except ValueError:
            days_since_first_review = 0
        days_since_first = max(days_since_first_review, days_since_first_commit)
        # since your first commit, how much of the life of the project have you been active?
        percent_active = how_many_days_active / float(days_since_first)
        rcolor = percent_active**2 * 0x7f + 0x7f
        bcolor = 0x60
        gcolor = 0

        pyplot.plot(x_vals, cumulative_data, linestyle='-', drawstyle='steps-pre',
                    label=person, linewidth=2, solid_capstyle="butt",
                    alpha=0.5, color='#333333')
        pyplot.plot(x_vals, commit_data, linestyle='-', drawstyle='steps-pre',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=1.0, color='#%.2x%.2x%.2x' % (rcolor, gcolor, bcolor))
        pyplot.plot(x_vals, review_data, linestyle='-', drawstyle='steps-pre',
                    label=person, linewidth=5, solid_capstyle="butt",
                    alpha=1.0, color='#00a400')
    pyplot.title('Contributor Actvity (as of %s)' % datetime.datetime.now().date())
    pyplot.ylabel('Contributor')
    person_labels.sort()
    pyplot.yticks([p[0] for p in person_labels], [p[1] for p in person_labels])
    pyplot.ylim(-1, person_labels[-1][0] + 1)
    x_tick_locs = []
    x_tick_vals = []
    for i, d in enumerate(all_dates):
        if i % 60:
            continue
        x_tick_locs.append(i)
        x_tick_vals.append(d)
    x_tick_locs.append(len(all_dates))
    x_tick_vals.append(all_dates[-1])
    pyplot.xticks(x_tick_locs, x_tick_vals, rotation=30, horizontalalignment='right')
    pyplot.xlim(-1, x_tick_locs[-1] + 1)
    pyplot.grid(b=True, which='both', axis='both')
    vertical_size_per_person = 0.25
    vertical_size = vertical_size_per_person * len(person_labels)
    horizontal_size_per_day = 0.02
    horizontal_size = horizontal_size_per_day * len(x_vals)
    fig = pyplot.gcf()
    fig.set_size_inches(horizontal_size, vertical_size)
    fig.set_frameon(False)
    fig.savefig('contrib_activity2.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

def draw_active_contribs_trends(actives_windows, actives, actives_avg, start_date, end_date):
    all_dates = list(date_range(start_date, end_date))
    x_vals = range(len(all_dates))
    for aw, rolling_avg_windows in actives_windows:
        pyplot.plot(x_vals, actives[aw], '-', alpha=0.5,
                    label="%d day activity window" % aw)
        for r_a_w in rolling_avg_windows:
            pyplot.plot(x_vals, actives_avg[aw][r_a_w], '-',
                        label="%d day avg (%d)" % (r_a_w, aw), linewidth=3)
    pyplot.title('Active contributors (as of %s)' % datetime.datetime.now().date())
    pyplot.ylabel('Contributor Count')
    pyplot.legend(loc='upper left')
    x_tick_locs = []
    x_tick_vals = []
    for i, d in enumerate(all_dates):
        if i % 60:
            continue
        x_tick_locs.append(i)
        x_tick_vals.append(d)
    x_tick_locs.append(len(all_dates))
    x_tick_vals.append(all_dates[-1])
    pyplot.xticks(x_tick_locs, x_tick_vals, rotation=30, horizontalalignment='right')
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.xlim(-1, x_tick_locs[-1] + 1)
    ax = pyplot.gca()
    fig = pyplot.gcf()
    fig.set_size_inches(24, 8)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('active_contribs2.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()


if __name__ == '__main__':
    # load patch info
    try:
        contribs_by_date, authors_by_count = load_commits(FILENAME)
        # update the data first
        most_recent_date = max(contribs_by_date.keys())
        most_recent_date = datetime.datetime.strptime(
            most_recent_date, '%Y-%m-%d').date()
        print 'Last date found in data file:', most_recent_date
        print 'Last date found in source repo:', LAST_DATE
        if most_recent_date < LAST_DATE:
            print 'Updating previous data with data since %s...' % most_recent_date
            recent_data, new_by_count = get_data(most_recent_date, LAST_DATE)
            for date in recent_data:
                if date in contribs_by_date:
                    contribs_by_date[date].update(recent_data[date])
                else:
                    contribs_by_date[date] = recent_data[date]
            for a, c in new_by_count.items():
                if a not in authors_by_count:
                    authors_by_count[a] = 0
                authors_by_count[a] += c
            save_commits(contribs_by_date, authors_by_count, FILENAME)
        else:
            print 'Data file (%s) is up to date.' % FILENAME
    except (IOError, ValueError), exc:
        print exc
        contribs_by_date, authors_by_count = get_data(FIRST_DATE, LAST_DATE)
        save_commits(contribs_by_date, authors_by_count, FILENAME)

    # load review info
    reviewers_by_date = load_reviewers(REVIEWS_FILENAME)

    # combine data sources down to one set of contributors and dates
    people_by_date = defaultdict(lambda: defaultdict(set))
    dates_by_person = defaultdict(lambda: defaultdict(set))
    first_contrib_date = min(contribs_by_date.keys())
    first_review_date = min(reviewers_by_date.keys())
    global_first_date = str(min(first_contrib_date, first_review_date))
    last_contrib_date = max(contribs_by_date.keys())
    last_review_date = max(reviewers_by_date.keys())
    global_last_date = str(max(last_contrib_date, last_review_date))
    print 'Global first date is:', global_first_date
    print 'Global last date is:', global_last_date

    actives_windows = [(180, (365, 730)), (90, (180, 365)), (14, (30, 90))]
    actives = {x: [] for (x, _) in actives_windows}
    rolling_sets = {x: RollingSet(x) for (x, _) in actives_windows}
    actives_avg = {x: defaultdict(list) for (x, _) in actives_windows}

    for date in date_range(global_first_date, global_last_date):
        contribs = contribs_by_date.get(date, set())
        reviews = reviewers_by_date.get(date, set())
        contribs = map_people(contribs)
        reviews = map_people(reviews)
        people_by_date[date]['contribs'] = contribs
        people_by_date[date]['reviews'] = reviews
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        contrib_window = datetime.timedelta(days=14)
        review_window = datetime.timedelta(days=5)
        for person in contribs:
            end_date = date_obj + contrib_window
            for d in date_range(date, end_date):
                dates_by_person[person]['contribs'].add(d)
                people_by_date[d]['contribs'].add(person)
        for person in reviews:
            end_date = date_obj + review_window
            for d in date_range(date, end_date):
                dates_by_person[person]['reviews'].add(d)
                people_by_date[d]['reviews'].add(person)

        # calcs for total active contribs
        for aw, rolling_avg_windows in actives_windows:
            active_today = set()
            active_today.update(people_by_date[date].get('contribs', set()))
            active_today.update(people_by_date[date].get('reviews', set()))
            rolling_sets[aw].add(active_today)
            actives[aw].append(len(rolling_sets[aw]))
            for r_a_w in rolling_avg_windows:
                denom = min(len(actives[aw]), r_a_w)
                s = sum(actives[aw][-r_a_w:])
                actives_avg[aw][r_a_w].append(float(s) / denom)

    print len(dates_by_person), 'total contributors found'

    # draw graphs
    # draw_contrib_activity_graph(dates_by_person, global_first_date, global_last_date)
    draw_active_contribs_trends(actives_windows, actives, actives_avg, global_first_date, global_last_date)
