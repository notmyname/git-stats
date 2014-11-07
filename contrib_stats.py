import json
import subprocess

from matplotlib import pyplot

# TODO: track contributor half-life
# TODO: derivative of totals
# TODO: figure out churn
# TODO: how long do patches stay in review (first proposal to merge time)

chunk_size = 180  # number of days for one "chunk" of time

def timeblock_iter():
    start = 0
    end = start + chunk_size
    while True:
        yield (start, end)
        start = end
        end += chunk_size

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
    starts = [x[0] for x in d]
    values = [x[1] for x in d]
    totals = [x[2] for x in d]
    pyplot.plot(starts, values, '-', color='blue', label='active')
    pyplot.plot(starts, totals, '-', color='red', label='cumulative')
    pyplot.title('Active contributors')
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    pyplot.legend(loc='upper left')
    ax = pyplot.gca()
    ax.invert_xaxis()
    fig = pyplot.gcf()
    fig.set_size_inches(6, 4)
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
