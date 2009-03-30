#!/usr/bin/env python
import re
import sys
import os
import urllib
from BeautifulSoup import BeautifulSoup
from PyRSS2Gen import RSSItem, Guid
import ScrapeNFeed
from datetime import datetime, timedelta
import pytz

sys.path += [os.path.join(os.path.dirname(__file__), 'icalendar')]
from icalendar import Calendar, Event

whitespace = re.compile("[\s]+|&nbsp;")

#
# Routine to pull out the text from a cell of the listing table,
# which can in turn have all kinds of crazy nested tags generated
# through the magic of FrontPage, or Word, or whatever it is.
#
def ExtractTableCellText(cell):
    while hasattr(cell, 'contents') and len(cell) > 0:
        cell = cell.contents[0]

    try:
        txt = cell.renderContents()
    except AttributeError:
        txt = str(cell)

    txt = whitespace.sub(' ', txt).strip()

    # print txt

    return txt

# Given a string like "LIVE 11AM" returns a tuple of (hour, minute,
# ampm, live) where hour and minute are ints, ampm is a string, and
# live is a bool
#
# Can also accept "LIVE NOON" as substitute for "LIVE 12PM"
# Can ignore idiotic typos like "LIVE 11:454AM" (Switzerland v Turkey, 6/11/08)
#
timeRe = re.compile("(?P<live>live)*\s*(?P<hour>(\d{1,2})|noon)([:](?P<minute>\d{1,2}))*[^amp]*(?P<ampm>am|pm)*", re.IGNORECASE)

def CrackTime(time):
    re_match = timeRe.match(time)

    if re_match == None:
        # print "no match ", time
        raise ValueError

    timeDict = re_match.groupdict()

    # get values that are optional
    if timeDict["minute"] == None:
        minute = 0;
    else:
        minute = int(timeDict["minute"])

    # convert "noon" to 12
    if str(timeDict["hour"]).lower() == "noon":
        hour = 12
        ampm = "pm"
    else:
        hour = int(timeDict["hour"])
        ampm = timeDict["ampm"]

    live = (timeDict["live"] != None)

    return (hour, minute, ampm, live)

# Given a string like "MON MAR 3", return a tuple of (year, month, day)
def CrackDate(date):
    match = re.match("([A-Za-z]*)\s+([A-Za-z]*)\s*(\d+)", date)
    if not match or not len(match.groups()) == 3:
        raise ValueError
    
    day, monthStr, date = match.groups()
    monthStr = monthStr.lower()
    date = int(date)

    now = datetime.now()

    monthDict = { "jan" : 1,
                  "feb" : 2,
                  "mar" : 3,
                  "apr" : 4,
                  "arp" : 4, # god bless dyslexia
                  "may" : 5,
                  "jun" : 6,
                  "jul" : 7,
                  "aug" : 8,
                  "sep" : 9,
                  "oct" : 10,
                  "nov" : 11,
                  "dec" : 12 }

    month = monthDict[monthStr[0:3]]
    
    year = now.year
    if (month < now.month):
        year += 1

    return (year, month, date)
    


#
# Build a list of matches that we find in the list
#
def BuildMatchList(soup):

    # Find the magic table with the crazy-ass background color
    table = soup.find(bgcolor="#000099")

    if table == None:
        table = soup.find(style="width: 100%; background-color: rgb(51, 102, 102);")

    # pull out all linebreaks, save ourselves headache later
    [br.extract() for br in table.findAll('br')]

    lastDate = ()

    result = []


    # loop over all rows, but skip the first; that's the header row
    stickyPrefix = ""
    
    for row in table.findAll('tr')[1:]:

        date, match, times = [ExtractTableCellText(cell) for cell in row.findAll('td')]

        # print "Date: (%s) Match: (%s) Times:(%s)" % (date, match, times)

        times = times.split("&amp;")

        prefix = ""

        if len(date) == 0:
            date_tuple = lastDate
        else:
            try:
                date_tuple = CrackDate(date)
                lastDate = date_tuple
            except ValueError:
                # doesn't have a valid date, is probably another
                # header row, like the Euro 2008 section
                date_tuple = lastDate
                if date == "RUGBY":
                    # print "rugby"
                    prefix = "%s: " % (date)
                elif match == "EURO 2008":
                    # print "euro 2008 header line"
                    stickyPrefix = "%s: " % (match)
                else:
                    print "Possibly bad date: date: %s match: %s times: %s" % (date, match, times)
                    prefix = "%s: " % (date)


        newPrefix = "%s %s" % (stickyPrefix, prefix)
        prefix = newPrefix.strip()
        if len(prefix) > 0:
            match = prefix + " " + match
            # print "New prefix: %s" % (prefix)
        
        for t in times:

            try:
                hour, minute, ampm, live = CrackTime(t)
            except ValueError:

                # TBA is a common invalid time, so let's not log that.
                # Also, the EURO 2008 header line has "TIMES" here, so
                # let's not log that either.  Cuts down on noise

                t = t.strip()

                if len(t) > 0                   \
                   and -1 == t.find("TBA")      \
                   and -1 == t.find("TAB")      \
                   and -1 == t.find("TB A")     \
                   and -1 == t.find("TIMES"):
                    print "bad time: ", t

                continue

            # print t, CrackTime(t)

            # If we don't get an am/pm match, assume pm.  You get this
            # when they forget to type a letter, as in "6M"
            #
            if ampm == None:
                ampm = "pm"

            # Get our final date and time...
            hour24 = hour
            if ampm.lower() == "pm" and hour24 < 12:
                hour24 += 12

            dtime = datetime(year=date_tuple[0], month=date_tuple[1],
                             day=date_tuple[2], hour=hour24, minute=minute)

            dtime = pytz.timezone('US/Pacific').localize(dtime)

            result.append( { "date" : dtime.ctime(),
                             "datetime" : dtime,
                             "match" : match,
                             "time" : t,
                             "hour" : hour,
                             "minute" : minute,
                             "ampm" : ampm,
                             "live" : live} )

    return result

matchList = BuildMatchList(BeautifulSoup(urllib.urlopen('http://www.georgeanddragonpub.com/football.html').read()))
# matchList = BuildMatchList(BeautifulSoup(open('football.html').read()))

cal = Calendar()
cal.add('prodid', '-//calendar parsing//floatplane.us//')
cal.add('version', '2.0')
cal.add('X-WR-CALNAME', 'Football on Telly')
cal.add('X-WR-TIMEZONE', 'America/Los Angeles')
cal.add('X-WR-CALDESC', 'Football on Telly at the George and Dragon, Seattle')


for match in matchList:

    live = ""
    if match["live"]:
        live = "(LIVE!)"
        
#     print """-------------------------------------------
#     date %s
#     match %s %s
#     time %d:%02d %s""" % ( match["date"], match["match"], live,
#                             match["hour"], match["minute"], match["ampm"])

#     print match

    event = Event()
    event.add('summary', "%s %s" % (match["match"], live))
    event.add('dtstart', match["datetime"])
    event.add('dtend', match["datetime"] + timedelta(hours=2))

    cal.add_component(event)

if len(sys.argv) > 1:
    f = open(sys.argv[1], "wb")
    f.write(cal.as_string())
    f.close()
