import datetime
import json
import unicodedata

COMMITS_FILENAME = 'contrib_stats.data'
CLIENT_COMMITS_FILENAME = 'client_contrib_stats.data'
REVIEWS_FILENAME = 'swift_gerrit_history.patches'
CLIENT_REVIEWS_FILENAME = 'swiftclient_gerrit_history.patches'
PEOPLE_MAP_FILENAME = '/Users/john/Documents/stackalytics/etc/default_data.json'
PERCENT_ACTIVE_FILENAME = 'percent_active.data'
AVERAGES_FILENAME = 'averages.data'

excluded_authors = (
    'Jenkins <jenkins@review.openstack.org>'.lower(),
    'Openstack Robot <jenkins@review.openstack.org>'.lower(),
    'OpenStack Proposal Bot <openstack-infra@lists.openstack.org>'.lower(),
    'OpenStack Robot <openstack-infra@lists.openstack.org>'.lower(),
    'OpenStack Jenkins <jenkins@openstack.org>'.lower(),
    'SwiftStack Cluster CI <openstack-ci@swiftstack.com>'.lower(),
    'Rackspace GolangSwift CI <mike+goci@weirdlooking.com>'.lower(),
    'Trivial Rebase <trivial-rebase@review.openstack.org>'.lower(),
    'Coraid CI <coraid-openstack-ci-all@mirantis.com>'.lower(),
    'Gerrit Code Review <review@openstack.org>'.lower(),
)

RELEASE_DATES = (
    '2010-07-19', # initial, 1.0.0
    '2010-10-21', # austin, 1.1.0
    '2011-02-03', # bexar, 1.2.0
    '2011-04-15', # cactus, 1.3.0
    '2011-05-27', # 1.4.0
    '2011-06-14', # 1.4.1
    '2011-07-25', # 1.4.2
    '2011-09-12', # diablo, 1.4.3
    '2011-11-24', # 1.4.4
    '2012-01-04', # 1.4.5
    '2012-02-08', # 1.4.6
    '2012-03-09', # 1.4.7
    '2012-03-22', # essex, 1.4.8
    '2012-06-05', # 1.5.0
    '2012-08-06', # 1.6.0
    # '2012-09-13', # 1.7.0
    # '2012-09-20', # 1.7.2
    '2012-09-26', # folsom, 1.7.4
    '2012-11-13', # 1.7.5
    '2013-04-04', # grizzly, 1.8.0
    '2013-07-02', # 1.9.0
    '2013-08-13', # 1.9.1
    '2013-10-17', # havana, 1.10.0
    '2013-12-12', # 1.11.0
    '2014-01-28', # 1.12.0
    '2014-03-03', # 1.13.0
    '2014-04-17', # icehouse, 1.13.1
    '2014-07-07', # 2.0.0
    '2014-09-01', # 2.1.0
    '2014-10-16', # juno, 2.2.0
    '2014-12-19', # 2.2.1
    '2015-02-02', # 2.2.2
    '2015-04-30', # kilo, 2.3.0
    '2015-09-01', # 2.4.0
    '2015-10-05', # liberty, 2.5.0
    '2016-01-25', # 2.6.0
    '2016-03-24', # mitaka, 2.7.0
    '2016-06-09', # 2.8.0
    '2016-07-14', # 2.9.0
)

def date_range(start_date, end_date, strings=True):
    '''yields an inclusive list of dates'''
    step = datetime.timedelta(days=1)
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date[:10], '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date[:10], '%Y-%m-%d')
    while start_date <= end_date:
        if strings:
            yield start_date.strftime('%Y-%m-%d')
        else:
            yield start_date
        start_date += step

the_people_map = {}

def load_the_people_map():
    raw_map = json.load(open(PEOPLE_MAP_FILENAME))
    users = raw_map['users']
    for record in users:
        name = record['user_name']
        for e in record['emails']:
            the_people_map[e] = name

load_the_people_map()

def map_one_person(person):
    person = unicodedata.normalize('NFKD', person).encode('ascii','ignore')
    name, email = person.split('<', 1)
    email = email[:-1].strip()
    name = name.strip()
    good_name = the_people_map.get(email, name)
    good_name = unicodedata.normalize('NFKD', unicode(good_name)).encode('ascii','ignore').title()
    return good_name

def map_people(unmapped_people):
    '''
    maps people by email to a name

    :param: unmapped_people is an iterable of 'name <email>'

    Lazy about non-ascii, lazy about name conflicts
    '''
    mapped_people = set()
    for person in unmapped_people:
        person = unicodedata.normalize('NFKD', person).encode('ascii','ignore')
        name, email = person.split('<', 1)
        email = email[:-1].strip()
        name = name.strip()
        good_name = the_people_map.get(email, name)
        good_name = unicodedata.normalize('NFKD', unicode(good_name)).encode('ascii','ignore').title()
        mapped_people.add(good_name)
    return mapped_people
