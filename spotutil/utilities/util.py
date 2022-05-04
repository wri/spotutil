import requests
import pytz
from dateutil import tz
from datetime import datetime, timedelta


def in_office():
    # check our external IP
    # if we're out of the office, will have to use private IP and VPN

    in_office = False

    # https://stackoverflow.com/a/36205547/4355916
    r = requests.get('https://api.ipify.org')
    ip = r.text

    if ip == '216.70.220.184':
        in_office = True

    return in_office


def days_hours_minutes(td):
    return td.seconds // 3600, (td.seconds // 60) % 60


def launchtime(response, r):
    launch = response['Reservations'][0]['Instances'][0]['LaunchTime']

    # convert launch time UTC to eastern time zone
    # https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime-with-python
    time_fmt = '%Y/%m/%d %H:%M'
    from_zone = tz.gettz('UTC')
    launch = launch.replace(tzinfo=from_zone)

    to_zone = pytz.timezone('US/Eastern')
    launch_time = launch.astimezone(
        to_zone)  # datetime.datetime(2018, 7, 19, 8, 44, tzinfo=<DstTzInfo 'US/Eastern' EDT-1 day, 20:00:00 DST>)

    # format launch time
    launch_time_f = launch_time.strftime(time_fmt)

    # to compare new offset-aware datetime, need to make "now" offset aware
    now = datetime.now()
    now = now.replace(tzinfo=to_zone)

    # format time now
    now_f = now.strftime(time_fmt)

    # get seconds difference between launchtime and now
    tdelta = datetime.strptime(now_f, time_fmt) - datetime.strptime(launch_time_f, time_fmt)

    # get h:m:s
    sec = tdelta.seconds
    hrs_min = timedelta(seconds=sec)

    hours, mins = days_hours_minutes(hrs_min)

    return '{0} hours, {1} minutes'.format(hours, mins)