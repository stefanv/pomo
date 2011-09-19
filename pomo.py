#!/usr/bin/env python

# Author: Stefan van der Walt <stefan@sun.ac.za>
# License: BSD

from __future__ import division

TASK_DURATION = 25

import argparse, time, os, warnings, itertools, collections, \
       datetime, sys, threading, multiprocessing

parser = argparse.ArgumentParser(description='Pomodoro timer')
parser.add_argument('-t', '--task', type=str,
                    help='description of task to work on')
parser.add_argument('-a', '--analyse', type=str,
                    help='analyse the given pomo log')
args = parser.parse_args()

try:
    import pynotify
    has_pynotify = True
except ImportError:
    has_pynotify = False

try:
    import gtk
    import gobject
    import appindicator
    has_gtk = True
except:
    has_gtk = False

def notify(title, message):
    global has_pynotify

    if has_pynotify:
        if not pynotify.init("icon-summary-body"):
            has_pynotify = False

        n = pynotify.Notification(title, message)
        n.set_urgency(pynotify.URGENCY_CRITICAL)

        if not n.show():
            has_pynotify = False

    if not has_pynotify:
        print "\n\n" + "*" * 50
        print title
        print message
        print "*" * 50 + "\n\n"

def get_time():
    return time.strftime('%Y/%m/%d %H:%M:%S')

def load_time(s):
    return datetime.datetime.strptime(s, '%Y/%m/%d %H:%M:%S')

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
    longest_name = 'No task longer than 0 minutes'
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

class PomoApplet:
    time = '00:00'

    def __init__(self, queue, task=""):
        self.queue = queue
        self.task = task

    def run(self):
        ind = appindicator.Indicator("pomo", "pomo-applet-active",
                                     appindicator.CATEGORY_APPLICATION_STATUS)
        ind.set_status(appindicator.STATUS_ACTIVE)
        ind.set_attention_icon("indicator-messages-new")

        time_menu = gtk.MenuItem("test")
        task_menu = gtk.MenuItem(self.task)

        menu = gtk.Menu()
        for m in (time_menu, task_menu):
            menu.append(m)
            m.show()

        ind.set_menu(menu)

        self._ind = ind
        self._menu = menu
        self._time_menu = time_menu

        gobject.timeout_add(1000, self.timeout_callback)

        gtk.main()

    def timeout_callback(self):
        self._time_menu.set_label(self.queue.get())
        return True

    def set_time(self, t):
        self.time = t

def build_applet(queue, task):
    applet = PomoApplet(queue, task)
    applet.run()

queue = multiprocessing.Queue()
applet_process = None
if has_gtk:
    applet_process = multiprocessing.Process(target=build_applet,
                                             args=(queue, args.task))
    applet_process.start()

notify('Your 25 minutes starts now',
       'Working on: %s' % args.task)

time0 = get_time()

for i in range(int(TASK_DURATION * 60), 0, -1):
    timer = queue.put(str(datetime.timedelta(seconds=i)))
    time.sleep(1)

time1 = get_time()

notify("Time's up!",
       'Take a 5 minute break...')

log_file = os.path.join(os.path.dirname(__file__), 'pomo.log')

try:
    with open(log_file, 'a') as f:
        f.writelines(l + "\n" for l in
                     (args.task or "Pomodoro",
                      time0,
                      time1,
                      ""))
except IOError:
    print 'Could not write to log file %s.' % log_file

if applet_process is not None:
    applet_process.terminate()
