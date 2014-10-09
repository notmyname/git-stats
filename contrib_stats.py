import subprocess

max_lookback = 2000
chunk_size = 30
all_chunks = []

i = 0
while i < max_lookback:
    start = i
    i += chunk_size
    if i > max_lookback:
        break
    end = i
    all_chunks.append((start, end))

for start, end in all_chunks:
    cmd = "git shortlog -nes --no-merges --before='@{%d days ago}' --since='@{%d days ago}' | wc -l" % (start, end)
    count = subprocess.check_output(cmd, shell=True)
    count.strip()
    print '%d\t%d\t%d' % (start, end, int(count))
