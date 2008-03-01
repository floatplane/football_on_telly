#!/usr/bin/env python
import re
from BeautifulSoup import BeautifulSoup
from PyRSS2Gen import RSSItem, Guid
import ScrapeNFeed

class FootyFeed(ScrapeNFeed.ScrapedFeed):    

    def HTML2RSS(self, headers, body):
        soup = BeautifulSoup.BeautifulSoup(body)

        table = soup.find(bgcolor="#000099")
        items = []
        for row in table.findAll('tr'):

            print row
#             link = self.baseURL + item.a['href']
#             if not self.hasSeen(link):
#                 bookTitle = item.a.string
#                 releaseDate = item.em.string
#                 items.append(RSSItem(title=bookTitle,
#                                      description=releaseDate,
#                                      link=link))
#         self.addRSSItems(items)

# FootyFeed.load("Football at the George & Dragon",
#                  'http://www.oreilly.com/catalog/new.html',
#                  "Keep track of O'Reilly books as they're announced",
#                  'footy.xml', 
# 		  'footy.pickle',
#                  managingEditor='leonardr@segfault.org (Leonard Richardson)')

whitespace = re.compile("[\s]+|&nbsp;")

def ExtractTableCellText(cell):
    while hasattr(cell, 'contents') and len(cell) > 0:
        cell = cell.contents[0]

    try:
        txt = cell.renderContents()
    except AttributeError:
        txt = str(cell)

    txt = whitespace.sub(' ', txt).strip()

    return txt

soup = BeautifulSoup(open('football.html').read())
#                     , convertEntities=BeautifulSoup.ALL_ENTITIES)
table = soup.find(bgcolor="#000099")

# pull out all linebreaks
[br.extract() for br in table.findAll('br')]

lastDate = ""

for row in table.findAll('tr')[1:]:

    date, misc, match, times = [ExtractTableCellText(cell) for cell in row.findAll('td')]

    times = times.split("&amp;")

    if len(date) == 0:
        date = lastDate
    else:
        lastDate = date

    for time in times:
        print """-------------------------------------------
        date %s
        misc %s
        match %s
        time %s""" % (date, misc, match, time)

    
    
