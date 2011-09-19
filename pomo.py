from __future__ import division

import argparse
import time
import json
import os
import warnings
import itertools
import collections
import datetime
import sys

parser = argparse.ArgumentParser(description='Pomodoro timer')
parser.add_argument('-t', '--task', type=str,
                    help='description of task to work on')
parser.add_argument('-a', '--analyse', type=str,
                    help='analyse the given pomo log')
args = parser.parse_args()

try:
    import pynotify
    notify = True
except ImportError:
    notify = False

def notify(title, message):
    if not notify or not pynotify.init("icon-summary-body"):
        print "\n\n" + "*" * 50
        print title
        print message
        print "\n\n" + "*" * 50
    else:
        n = pynotify.Notification(title, message)

def get_time():
    return time.strftime('%Y/%m/%d %H:%M')

def load_time(s):
    return datetime.datetime.strptime(s, '%Y/%m/%d %H:%M')

def group(lst, n):
    """group([0,3,4,10,2,3], 2) => iterator

    Group an iterable into an n-tuples iterable. Incomplete tuples
    are discarded e.g.

    >>> list(group(range(10), 3))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]

    http://code.activestate.com/recipes/
    303060-group-a-list-into-sequential-n-tuples/

    """
    return itertools.izip(
        *[itertools.islice(lst, i, None, n) for i in range(n)])

def report(data):
    data = [l.strip() for l in data]
    data = [l for l in data if l]

    L = len(data)
    if (L / 3) != (L // 3):
        print 'Log file contains invalid number of lines. '
        print 'Trying to proceed anyway.'
        data = data[:L - (L % 3)]

    pomos = collections.OrderedDict()
    total_today = datetime.timedelta()
    for (task, start, end) in group(data, 3):
        start = load_time(start)
        end = load_time(end)
        
        if task not in pomos:
            pomos[task] = {'nr': 0,
                           'time': datetime.timedelta()}

        pomos[task]['nr'] += 1
        delta = (end - start)
        pomos[task]['time'] += delta

        if end.date() == datetime.datetime.today().date():
            total_today += delta

    print "Task summary [pomos]"
    print "--------------------"
    for task in pomos:
        print '%s [%d]' % (task, pomos[task]['nr'])
    print

    total = datetime.timedelta()
    longest_time = datetime.timedelta()
    for name, task in pomos.items():
        duration = task['time']
        total += task['time']

        if duration > longest_time:
            longest_time = duration
            longest_name = name

    print "Time summary"
    print "------------"
    print "Total time for today:", total_today
    print "Total time:", total
    print "Longest task: %s at %s" % (longest_name, longest_time)


if args.analyse is not None:
    try:
        with open(args.analyse, 'r') as f:
            report(f.readlines())

    except IOError:
        print 'Cannot load "%s" for analysis.' % args.analyse
        sys.exit(-1)

    sys.exit(0)


time0 = get_time()

time1 = get_time()

log_file = os.path.join(os.path.dirname(__file__), 'pomo.log')

try:
    with open(log_file, 'a') as f:
        f.writelines(l + "\n" for l in
                     (args.task or "Pomodoro",
                      time0,
                      time1,
                      ""))
except IOError:
    config = {}
