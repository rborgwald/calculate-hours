#!/usr/bin/python

# To set this script up, follow instructions at https://developers.google.com/calendar/quickstart/python
# Also, you might need to run: pip3 install --upgrade google-api-python-client

from __future__ import print_function
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from configparser import ConfigParser
import datetime
import sys
import pytz
import re

def addColonToTimeZone(datetime):
    return re.sub(r'(.*)(00)', r'\1:\2', datetime)

def removeColonFromTimeZone(datetime):
    return re.sub(r'(.*):(00)', r'\1\2', datetime)

def computeStartTime(startDate):
    local_tz = pytz.timezone("US/Central")
    datetime_without_tz = datetime.datetime.strptime(startDate, '%m/%d/%Y')
    datetime_with_tz = local_tz.localize(datetime_without_tz, is_dst=None).strftime('%Y-%m-%dT%H:%M:%S%z')
    return addColonToTimeZone(datetime_with_tz)

def getStartOfDayDateTime(date):
    local_tz = pytz.timezone("US/Central")
    datetime_without_tz = datetime.datetime.combine(date, datetime.time.min)
    datetime_with_tz = local_tz.localize(datetime_without_tz, is_dst=None)
    return datetime_with_tz

def getEndOfDayDateTime(date):
    local_tz = pytz.timezone("US/Central")
    datetime_without_tz = datetime.datetime.combine(date, datetime.time.max)
    datetime_with_tz = local_tz.localize(datetime_without_tz, is_dst=None)
    return datetime_with_tz

def computeStopTime(startDate, numberOfDays):
    local_tz = pytz.timezone("US/Central")
    start_date_without_tz = datetime.datetime.strptime(startDate, '%m/%d/%Y')
    end_date_without_tz = start_date_without_tz + datetime.timedelta(days=numberOfDays + 1)
    datetime_with_tz = local_tz.localize(end_date_without_tz, is_dst=None).strftime('%Y-%m-%dT%H:%M:%S%z')
    return addColonToTimeZone(datetime_with_tz)

def calculateHoursForDay(date, daysActions):
    minutes = 0
    startOfDay = getStartOfDayDateTime(date)
    startWorkTime = None
    if len(daysActions) == 0:
        return minutes

    # check if first action is a stop
    if daysActions[0]['action'] == 'You exited work':
        minutes += (daysActions[0]['timestamp'] - startOfDay) / datetime.timedelta(minutes=1)
    for a in daysActions:
        if a['action'] == 'You entered work':
            startWorkTime = a['timestamp']
        elif a['action'] == 'You exited work' and startWorkTime != None:
            minutes += (a['timestamp'] - startWorkTime) / datetime.timedelta(minutes=1)
            startWorkTime = None

    # check if last action is a start
    if daysActions[-1]['action'] == 'You entered work':
        endOfDay = getEndOfDayDateTime(date)
        minutes += (endOfDay - daysActions[-1]['timestamp']) / datetime.timedelta(minutes=1)

    return round(minutes / 60, 2)

def calculateHours(events):
    daysDict = {}

    # Group events into days
    for event in events:
        dateTimeStr = event['start'].get('dateTime')
        dateTime = datetime.datetime.strptime(removeColonFromTimeZone(dateTimeStr), '%Y-%m-%dT%H:%M:%S%z')
        dateStr = dateTime.date()
        eventSummary = { 'timestamp': dateTime, 'action': event['summary']}
        if dateStr in daysDict:
            daysDict[dateStr]['summaries'].append(eventSummary)
        else:
            data = {'summaries': [eventSummary]}
            daysDict[dateStr] = data

    # Calculate hours for each day
    for date in daysDict:
        hours = calculateHoursForDay(date, daysDict[date]['summaries'])
        daysDict[date].update({'hours': hours})

    return daysDict

def main():
    numberOfDays = 7
    if len(sys.argv) < 2:
        raise RuntimeError(
            f'Incorrect number of arguments: {len(sys.argv)}. Expected at least one (mm/dd/YYYY). A second optional arg for number of days (default is 7).')
    else:
        startDate = sys.argv[1]
        if (len(sys.argv) > 2):
            numberOfDays = int(sys.argv[2])

    startTime = computeStartTime(startDate)
    stopTime = computeStopTime(startDate, numberOfDays)

    # Setup the Calendar API
    config = ConfigParser()
    config.read('calendar.ini')
    calendar_id = config.get('google_calendar', 'calendar_id')
    url = config.get('google_calendar', 'url')

    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secrets.json', url)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Call the Calendar API
    print('Getting work events')
    events_result = service.events().list(calendarId=calendar_id,
                                          timeMin=startTime,
                                          timeMax=stopTime,
                                          singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    # for event in events:
    #     start = event['start'].get('dateTime')
    #     print(start, event['summary'])

    days = calculateHours(events)

    print()
    print(f'Date           Hours Worked\n---------------------------')
    totalHours = 0
    for key, value in days.items():
        totalHours += value["hours"]
        print(f'{key}     {value["hours"]}')
    print()
    print(f'Total Hours:   {round(totalHours, 2)}')



if __name__ == "__main__":
    main()