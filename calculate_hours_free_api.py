#!/usr/bin/python

import sys
import requests
import time
import pytz
import datetime

from collections import namedtuple

Action = namedtuple('Action', 'id, userId, topicId, name, timestamp')

# date format must be m/d/YYYY
def convertLocalDateToEpoch(date):
    local_tz = pytz.timezone("US/Central")
    datetime_without_tz = datetime.datetime.strptime(date, "%m/%d/%Y")
    datetime_with_tz = local_tz.localize(datetime_without_tz, is_dst=None)
    datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
    epoch = int(datetime_in_utc.timestamp()) * 1000
    return epoch

#convert epoch millis to date format
def getDateFromTimestamp(timestampUtc):
    return time.strftime('%m/%d/%Y', time.gmtime(timestampUtc / 1000.))

# create a dict entry for each day
#{1: {'date': '04/22/2018', 'startTime': 1524373200000, 'endTime': 1524459599000}, 2: { ... } }
def createDaysDict(startDate, numberOfDays):
    daysDict = {}
    currentTimestamp = convertLocalDateToEpoch(startDate)
    for d in range(numberOfDays):
        daysDict[d + 1] = { 'date': getDateFromTimestamp(currentTimestamp),'startTime': currentTimestamp, 'endTime': currentTimestamp + 86399000}
        currentTimestamp += 86400000
    return daysDict

# returns actions that happened on the supplied day
def filterActions(dayData, allActions):
    dayActions = []
    for a in allActions:
        if a.timestamp >= dayData['startTime'] and a.timestamp <= dayData['endTime']:
            dayActions.append(a)
    return dayActions

# calculates the number of hours worked for the specified date
def calculateHoursForDay(date, daysActions, startAction, stopAction):
    hours = 0
    startTime = 0

    if len(daysActions) == 0:
        return hours

    # check if first action is a stop
    if daysActions[0].name == stopAction:
        hours += (daysActions[0].timestamp - convertLocalDateToEpoch(date)) / 3600000

    for a in daysActions:
        if a.name == startAction:
            startTime = a.timestamp
        elif a.name == stopAction and startTime != 0:
            hours += (a.timestamp - startTime) / 3600000
            startTime = 0

    # check if last action is a start
    if daysActions[-1].name == startAction:
        lastMilliOfDay = convertLocalDateToEpoch(date) + 86399000
        hours += (lastMilliOfDay - daysActions[-1].timestamp) / 3600000

    return round(hours, 2)

# Adds 'hours' field to each day in the dictionary
# {1: {'date': '04/22/2018', 'startTime': 1524373200000, 'endTime': 1524459599000, 'hours': 0}, 2: { ... } }
def updateDictWithHoursWorked(dict, actions, startAction, stopAction):
    for d in dict:
        actionsForDay = filterActions(dict[d], actions)
        #print(f'{dict[d]["date"]}: {actionsForDay}')
        hours = calculateHoursForDay(dict[d]["date"], actionsForDay, startAction, stopAction)
        dict[d].update({'hours': hours})

def main():
    numberOfDays = 7
    if len(sys.argv) < 2:
        raise RuntimeError(f'Incorrect number of arguments: {len(sys.argv)}. Expected at least one (mm/dd/YYYY). A second optional arg for number of days (default is 7).')
    else:
        startDate = sys.argv[1]
        if(len(sys.argv) > 2):
            numberOfDays = int(sys.argv[2])

    daysDict = createDaysDict(startDate, numberOfDays)

    minimumTimestamp = daysDict[1]['startTime']
    maximumTimestamp = daysDict[numberOfDays]['endTime']
    URL = 'http://placetracking.appspot.com/api/v3/actions/get/'
    topicId = 'ENTER YOUR TOPIC ID'
    startAction = 'start'
    stopAction = 'stop'
    PARAMS = {'topicId': topicId, 'minimumTimestamp': minimumTimestamp, 'maximumTimestamp': maximumTimestamp}

    r = requests.get(url=URL, params=PARAMS)
    data = r.json()

    actions = {}
    if 'content' in data.keys():
        actions = [Action(**k) for k in data['content']]
        actions.sort(key = lambda x: x.timestamp)

    for a in actions:
        localtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(a.timestamp/1000))

    updateDictWithHoursWorked(daysDict, actions, startAction, stopAction)
    print()
    print(f'Date           Hours Worked\n---------------------------')
    totalHours = 0
    for key, value in daysDict.items():
        totalHours += value["hours"]
        print(f'{value["date"]}     {value["hours"]}')
    print()
    print(f'Total Hours:   {totalHours}')

if __name__== "__main__":
    main()





