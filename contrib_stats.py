import subprocess

chunk_size = 30  # number of days for one "chunk" of time

def timeblock_iter():
    start = 0
    end = start + chunk_size
    while True:
        yield (start, end)
        start = end
        end += chunk_size

for start, end in timeblock_iter():
    cmd = "git shortlog -nes --no-merges --before='@{%d days ago}' --since='@{%d days ago}' | wc -l" % (start, end)
    count = subprocess.check_output(cmd, shell=True)
    count.strip()
    count = int(count)
    if count <= 0:
        break
    print '%d\t%d\t%d' % (start, end, count)
