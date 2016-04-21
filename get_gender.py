#!/usr/bin/env python

import requests
import json
import random

# from https://github.com/block8437/gender.py
def getGenders(names):
    url = ""
    cnt = 0
    for name in names:
        if url == "":
            url = "name[0]=" + name
        else:
            cnt += 1
            url = url + "&name[" + str(cnt) + "]=" + name

    req = requests.get("http://api.genderize.io?" + url)
    try:
        results = json.loads(req.text)
    except ValueError:
        print req.status_code
        print req.headers
        print req.content
        return [(u'None',u'0.0',0.0)] * len(names)
    
    retrn = []
    for result in results:
        if result["gender"] is not None:
            retrn.append((result["gender"], result["probability"], result["count"]))
        else:
            retrn.append((u'None',u'0.0',0.0))
    return retrn


with open('percent_active.data', 'rb') as f:
    names = [x.split(':')[0].strip() for x in f.readlines()]

first_names = [x.split(' ')[0].strip() for x in names]

try:
    name_gender = json.load(open('genders.data', 'rb'))
except:
    genders = getGenders(first_names)
    name_gender = zip(names, genders)
    json.dump(name_gender, open('genders.data', 'wb'))

male = female = 0
for x in name_gender:
    if x[1][0] == 'male':
        male += 1
    else:
        female += 1

total = float(male + female)
print '%.2f%% Male' % (100 * male / total)
print '%.2f%% Female' % (100 * female / total)

