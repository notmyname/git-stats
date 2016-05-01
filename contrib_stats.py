import sys
import datetime
import subprocess
from collections import defaultdict
import json
import re
from matplotlib import pyplot
import unicodedata

from utils import RELEASE_DATES, excluded_authors, COMMITS_FILENAME, \
    CLIENT_COMMITS_FILENAME, REVIEWS_FILENAME, CLIENT_REVIEWS_FILENAME, \
    PERCENT_ACTIVE_FILENAME, date_range, map_people, map_one_person, \
    AVERAGES_FILENAME
from parse_commits_into_json import load_commits


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
                # name_email = name_email.decode('utf8')
                name_email = '%s %s' % (map_one_person(name_email), email)
                if name_email.lower() in excluded_authors:
                    continue
                reviewers_by_date[when].add(name_email)
    return reviewers_by_date

def draw_contrib_activity_graph(dates_by_person, start_date, end_date, extra_window):
    # this graph will show a little bit of the future
    end_date = datetime.datetime.strptime(end_date[:10], '%Y-%m-%d') + extra_window
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
    person_active = []
    limited_all_dates_look_back = 365 * 1
    for person, (yval, commit_data, review_data, cumulative_data, sparse_cumulative_data) in graphable_data.iteritems():
        name = person.split('<', 1)[0].strip()
        person_labels.append((yval, name))
        how_many_days_active_total = sparse_cumulative_data.count(yval)
        how_many_days_active_limited = sparse_cumulative_data[-limited_all_dates_look_back:].count(yval)
        how_many_days_active_limited2 = sparse_cumulative_data[-limited_all_dates_look_back*2:-limited_all_dates_look_back].count(yval)
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
        percent_active = how_many_days_active_total / float(days_since_first)
        cumulative_percent_active = how_many_days_active_limited / float(limited_all_dates_look_back)
        cumulative_percent_active2 = how_many_days_active_limited2 / float(limited_all_dates_look_back)
        weight = cumulative_percent_active + (cumulative_percent_active2 * .25)
        person_active.append((name, weight))
        rcolor = percent_active * 0xff
        bcolor = 0
        gcolor = 0
        activity_color = '#%02x%02x%02x' % (rcolor, gcolor, bcolor)
        review_color = '#%02x%02x%02x' % (106, 171, 62)
        commit_color = '#%02x%02x%02x' % (37, 117, 195)

        pyplot.plot(x_vals, cumulative_data, linestyle='-',
                    label=person, linewidth=3, solid_capstyle="butt",
                    alpha=1.0, color=activity_color)
        pyplot.plot(x_vals, commit_data, linestyle='-',
                    label=person, linewidth=10, solid_capstyle="butt",
                    alpha=1.0, color=commit_color)
        pyplot.plot(x_vals, review_data, linestyle='-',
                    label=person, linewidth=5, solid_capstyle="butt",
                    alpha=1.0, color=review_color)
        label_xval = cumulative_data.index(yval) - 3  # move over some for room
        pyplot.annotate(name, xy=(label_xval, yval - 0.25), horizontalalignment='right', color=activity_color)
    pyplot.title('Contributor Actvity (as of %s)' % datetime.datetime.now().date())
    pyplot.yticks([], [])
    person_labels.sort()
    pyplot.ylim(-1, person_labels[-1][0] + 1)
    x_tick_locs = []
    x_tick_vals = []
    today = str(datetime.datetime.now())[:10]
    for i, d in enumerate(all_dates):
        if d in RELEASE_DATES:
            pyplot.axvline(x=i, alpha=0.3, color='#469bcf', linewidth=2)
        if not i % 60:
            x_tick_locs.append(i)
            x_tick_vals.append(d)
        if d == today:
            pyplot.axvline(x=i, alpha=0.8, color='#cf9b46', linewidth=2)
    x_tick_locs.append(len(all_dates))
    x_tick_vals.append(all_dates[-1])
    pyplot.xticks(x_tick_locs, x_tick_vals, rotation=30, horizontalalignment='right')
    pyplot.xlim(-5, x_tick_locs[-1] + 20)
    pyplot.grid(b=True, which='both', axis='x')
    vertical_size_per_person = 0.3
    vertical_size = vertical_size_per_person * len(person_labels)
    horizontal_size_per_day = 0.02
    horizontal_size = horizontal_size_per_day * len(x_vals)
    ax = pyplot.gca()
    ax.set_frame_on(False)
    fig = pyplot.gcf()
    fig.set_size_inches(horizontal_size, vertical_size)
    fig.savefig('contrib_activity.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # maybe a bad place, but we have the percent active per person, so write it out
    with open(PERCENT_ACTIVE_FILENAME, 'wb') as f:
        for pers, perc in person_active:
            f.write('%s:%s\n' % (pers, perc))

def draw_active_contribs_trends(actives_windows, actives, actives_avg, start_date, end_date):
    all_dates = list(date_range(start_date, end_date))
    x_vals = range(len(all_dates))
    for aw, rolling_avg_windows in actives_windows:
        for r_a_w in rolling_avg_windows:
            pyplot.plot(x_vals, actives_avg[aw][r_a_w], '-',
                        label="%d day avg (of %d day total)" % (r_a_w, aw), linewidth=3)
    pyplot.title('Active contributors (as of %s)' % datetime.datetime.now().date())
    pyplot.ylabel('Contributor Count')
    pyplot.legend(loc='upper left')
    x_tick_locs = []
    x_tick_vals = []
    for i, d in enumerate(all_dates):
        if d in RELEASE_DATES:
            pyplot.axvline(x=i, alpha=0.3, color='#469bcf', linewidth=2)
        if not i % 60:
            x_tick_locs.append(i)
            x_tick_vals.append(d)
    x_tick_locs.append(len(all_dates))
    if len(all_dates) - x_tick_locs[-1] > 30:
        x_tick_vals.append(all_dates[-1])
    pyplot.xticks(x_tick_locs, x_tick_vals, rotation=30, horizontalalignment='right')
    pyplot.grid(b=True, which='both', axis='both')
    pyplot.xlim(-1, x_tick_locs[-1] + 1)
    ax = pyplot.gca()
    fig = pyplot.gcf()
    fig.set_size_inches(24, 8)
    fig.set_frameon(False)
    fig.savefig('active_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # small verison
    window = 90
    for aw, rolling_avg_windows in actives_windows:
        for r_a_w in rolling_avg_windows[:1]:  # the first window configured
            pyplot.plot(x_vals[:window], actives_avg[aw][r_a_w][-window:], '-',
                        label="%d day avg (of %d day total)" % (r_a_w, aw), linewidth=3)
    pyplot.grid(b=False, which='both', axis='both')
    pyplot.xticks([], [])
    pyplot.yticks([], [])
    pyplot.xlim(-1, window + 1)
    ax = pyplot.gca()
    ax.set_frame_on(True)
    ax.set_axis_bgcolor('black')  # change to (24, 24, 24)
    fig = pyplot.gcf()
    fig.set_size_inches(2, 2./3)
    fig.savefig('active_contribs_small.png', bbox_inches='tight', pad_inches=0)
    pyplot.close()

def draw_total_contributors_graph(people_by_date, start_date, end_date):
    all_dates = list(date_range(start_date, end_date))
    x_vals = range(len(all_dates))
    total_yvals = []
    reviewers_yvals = []
    authors_yvals = []
    total_set_of_contributors = set()
    total_set_of_reviewers = set()
    total_set_of_authors = set()
    for date in date_range(start_date, end_date):
        todays_total = set()
        todays_reviewers = people_by_date[date]['reviews']
        todays_authors = people_by_date[date]['contribs']
        todays_total.update(todays_reviewers)
        todays_total.update(todays_authors)
        total_set_of_contributors.update(todays_total)
        total_set_of_reviewers.update(todays_reviewers)
        total_set_of_authors.update(todays_authors)
        total_yvals.append(len(total_set_of_contributors))
        reviewers_yvals.append(len(total_set_of_reviewers))
        authors_yvals.append(len(total_set_of_authors))

    lens = map(len, [total_yvals, reviewers_yvals, authors_yvals])
    assert len(set(lens)) == 1, lens

    pyplot.plot(x_vals, total_yvals, '-', color='red',
               label="Total contributors", drawstyle="steps", linewidth=3)
    pyplot.plot(x_vals, reviewers_yvals, '-', color='green',
               label="Total reviewers", drawstyle="steps", linewidth=3)
    pyplot.plot(x_vals, authors_yvals, '-', color='blue',
               label="Total authors", drawstyle="steps", linewidth=3)
    pyplot.title('Total contributors (as of %s)' % datetime.datetime.now().date())
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    x_tick_locs = []
    x_tick_vals = []
    for i, d in enumerate(all_dates):
        if d in RELEASE_DATES:
            pyplot.axvline(x=i, alpha=0.3, color='#469bcf', linewidth=2)
        if not i % 60:
            x_tick_locs.append(i)
            x_tick_vals.append(d)
    x_tick_locs.append(len(all_dates))
    if len(all_dates) - x_tick_locs[-1] > 30:
        x_tick_vals.append(all_dates[-1])
    pyplot.xticks(x_tick_locs, x_tick_vals, rotation=30, horizontalalignment='right')
    pyplot.xlim(-1, x_tick_locs[-1] + 1)
    pyplot.grid(b=True, which='both', axis='both')
    fig = pyplot.gcf()
    fig.set_size_inches(24, 8)
    fig.savefig('total_contribs.png', bbox_inches='tight', pad_inches=0.25)
    pyplot.close()

    # small verison
    window = 90
    pyplot.plot(x_vals[:window], total_yvals[-window:], '-', color='red',
               label="Total contributors", drawstyle="steps", linewidth=3)
    pyplot.grid(b=False, which='both', axis='both')
    pyplot.xticks([], [])
    pyplot.yticks([], [])
    pyplot.xlim(-1, window + 1)
    ax = pyplot.gca()
    ax.set_frame_on(True)
    ax.set_axis_bgcolor('black')  # change to (24, 24, 24)
    fig = pyplot.gcf()
    fig.set_size_inches(2, 2. / 3)
    fig.savefig('total_contribs_small.png', bbox_inches='tight', pad_inches=0)
    pyplot.close()


if __name__ == '__main__':
    # load patch info
    contribs_by_date, ts_by_person = load_commits()
    # update the data first
    most_recent_date = max(contribs_by_date.keys())
    most_recent_date = datetime.datetime.strptime(
        most_recent_date, '%Y-%m-%d').date()
    print 'Last date found in data file:', most_recent_date
    print 'Last date found in source repo:', LAST_DATE

    # load review info
    reviewers_by_date = load_reviewers(REVIEWS_FILENAME)
    client_reviewers_by_date = load_reviewers(CLIENT_REVIEWS_FILENAME)
    for d, person_set in client_reviewers_by_date.iteritems():
        reviewers_by_date[d].update(person_set)

    contrib_window = datetime.timedelta(days=14)
    review_window = datetime.timedelta(days=3)

    # combine data sources down to one set of contributors and dates
    people_by_date = defaultdict(lambda: defaultdict(set))
    dates_by_person = defaultdict(lambda: defaultdict(set))
    first_contrib_date = min(contribs_by_date.keys())
    first_review_date = min(reviewers_by_date.keys())
    global_first_date = str(min(first_contrib_date, first_review_date))
    last_contrib_date = max(contribs_by_date.keys())
    last_review_date = max(reviewers_by_date.keys())
    global_last_date = str(max(last_contrib_date, last_review_date))
    msg = []
    msg.append('Global first date is: %s' % global_first_date)
    msg.append('Global last date is: %s' % global_last_date)
    unique_reviewer_set = set()

    actives_windows = [
        # (days, (rolling_avg_span, ...))
        (30, (180, 365)),
        (7, (30, 180)),
    ]
    actives = {x: [] for (x, _) in actives_windows}
    rolling_sets = {x: RollingSet(x) for (x, _) in actives_windows}
    actives_avg = {x: defaultdict(list) for (x, _) in actives_windows}

    for date in date_range(global_first_date, global_last_date):
        contribs = contribs_by_date.get(date, set())
        reviews = reviewers_by_date.get(date, set())
        mapped_contribs = set()
        for person in contribs:
            name, email = person.split('<', 1)
            email = '<' + email
            p = '%s %s' % (map_one_person(person), email)
            if p.lower() in excluded_authors:
                continue
            mapped_contribs.add(name)
        mapped_reviews = set()
        for person in reviews:
            name, email = person.split('<', 1)
            email = '<' + email
            p = '%s %s' % (map_one_person(person), email)
            if p.lower() in excluded_authors:
                continue
            mapped_reviews.add(name)
        people_by_date[date]['contribs'] = mapped_contribs
        people_by_date[date]['reviews'] = mapped_reviews
        unique_reviewer_set.update(mapped_reviews)
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        # next interesting thing to do here is make more than one event per day count more
        # right now all we're really calculating is person-day activity
        for person in mapped_contribs:
            end_date = date_obj + contrib_window
            for d in date_range(date, end_date):
                dates_by_person[person]['contribs'].add(d)
                people_by_date[d]['contribs'].add(person)
        for person in mapped_reviews:
            end_date = date_obj + review_window
            for d in date_range(date, end_date):
                dates_by_person[person]['reviews'].add(d)
                people_by_date[d]['reviews'].add(person)

        # Calculate the total active contributor count for a given
        # number of days. Then also make a moving average of that.
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

    msg.append('%d patch authors found' % len(ts_by_person))
    msg.append('%d review commentors found' % len(unique_reviewer_set))
    msg.append('%d total unique contributors found' % len(dates_by_person))
    msg = '\n'.join(msg)
    print msg

    with open(AVERAGES_FILENAME, 'wb') as f:
        data = [actives_windows, actives_avg]
        json.dump(data, f)

    # draw graphs
    draw_contrib_activity_graph(dates_by_person, global_first_date, global_last_date, max(contrib_window, review_window))
    draw_active_contribs_trends(actives_windows, actives, actives_avg, global_first_date, global_last_date)
    draw_total_contributors_graph(people_by_date, global_first_date, global_last_date)
