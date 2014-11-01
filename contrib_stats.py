import subprocess

from matplotlib import pyplot

chunk_size = 7  # number of days for one "chunk" of time

def timeblock_iter():
    start = 0
    end = start + chunk_size
    while True:
        yield (start, end)
        start = end
        end += chunk_size

def get_data():
    data = []
    zeros_found = 0
    for start, end in timeblock_iter():
        cmd = "git shortlog -nes --no-merges --before='@{%d days ago}' --since='@{%d days ago}' | wc -l" % (start, end)
        count = subprocess.check_output(cmd, shell=True)
        count.strip()
        count = int(count)
        if count <= 0:
            zeros_found += 1
        if zeros_found >= 5:  # more than 5 chunks at 0 is our escape valve
            break
        data.append((start, end, count))
    return data

def make_graph():
    d = get_data()
    d.reverse()
    starts = [x[0] for x in d]
    values = [x[2] for x in d]
    pyplot.plot(starts, values, '-', drawstyle='steps-mid')  #, color='white')
    pyplot.title('Active contributors')
    pyplot.xlabel('Days Ago')
    pyplot.ylabel('Contributors')
    ax = pyplot.gca()
    ax.invert_xaxis()
    #ax.set_axis_bgcolor('black')
    fig = pyplot.gcf()
    fig.set_size_inches(16, 4)
    fig.dpi = 200
    fig.set_frameon(True)
    fig.savefig('active_contribs.png', bbox_inches='tight', pad_inches=0.25)

make_graph()
