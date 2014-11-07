import json
import subprocess

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

def get_data():
    data = []
    for start, end in timeblock_iter():
        cmd = "git shortlog -nes --no-merges --before='@{%d days ago}' --since='@{%d days ago}' | wc -l" % (start, end)
        count = subprocess.check_output(cmd, shell=True)
        count.strip()
        count = int(count)
        aggregate_cmd = "git shortlog -nes --no-merges --before='@{%d days ago}' | wc -l" % start
        total = subprocess.check_output(aggregate_cmd, shell=True)
        total.strip()
        total = int(total)
        if total <= 0:
            break
        data.append((start, count, total))
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
        raw_data = json.load(f)
except (IOError, ValueError):
    raw_data = get_data()
    with open(filename, 'wb') as f:
        json.dump(raw_data, f)
make_graph(raw_data)
