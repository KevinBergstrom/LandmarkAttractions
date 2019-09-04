import os
import sys
from bs4 import BeautifulSoup
from lxml import etree
import requests
import csv
import re

#incase your connection keeps getting interrupted
STARTNEW = True

def setAction(whatAction):
	return 'action='+whatAction+'&'

def setFormat(whatFormat):
	return 'format='+whatFormat+'&'

def searchFor(searchTerms, limit):
	return 'search='+searchTerms+'&limit='+limit+'&'

def setProp(whatProp):
	return 'prop='+whatProp+'&'

def titles(whatTitles):
	listOfTitles = ''
	for title in whatTitles:
		listOfTitles += title+"|"
	return 'titles='+listOfTitles[:-1]+'&'

def getPage(url):
	page = requests.get(url)
	return page

def searchWikiURL(wikiURL, searchTerms, limit):
	return wikiURL+setAction('opensearch')+setFormat('xml')+searchFor(searchTerms, limit)

def queryWikiURL(wikiURL, queryTerms):
	return wikiURL+setAction('query')+setFormat('xml')+titles(queryTerms)
	
	
def pp(e):
    print(etree.tostring(e, pretty_print=True))
    print('')

def strip_ns(tree):
    for node in tree.iter():
        try:
            has_namespace = node.tag.startswith('{')
        except AttributeError:
            continue
        if has_namespace:
            node.tag = node.tag.split('}', 1)[1]

def stripString(str):
	newStr = str
	#remove unwanted stuff
	newStr = newStr.replace("\xa0","")
	newStr = newStr.replace("\n","")
	newStr = newStr.replace("\u2009","")
	#remove anything after the )
	newStr = re.sub("\)(.*)",")",newStr)
	newStr = re.sub("\[(\d*)\]","",newStr)
	#return stripped string
	return newStr

def scrapePage(link, pageType):

#scrape a page about a Name, Size, Location, Latitude, Longitude, Image, Type, Description
	htmlPage = getPage(link)
	mySoup = BeautifulSoup(htmlPage.content, "html.parser")
	#predefine data list
	scrapedData = ["No name","No size","No location","No longitude", "No latitude", "No image","No Type","No Description"]
	#get the whole article header
	mtnName = mySoup.h1.string
	scrapedData[0] = mtnName

	if mtnName is None:
		return []

	if "Bridge" in mtnName:
		pageType = "Bridge"

	#figure out what type it is
	mountainTags = ['Elevation']
	bridgeTags = ['Total length']
	buildingTags = ['Architectural','Roof','Top Floor','Antenna spire','Height']
	excludeTags = ['Destroyed','Demolished','Founded']
	plannedTags = ['Proposed', 'Under construction','Approved']

	if pageType is "Mountain":
		for i in range(len(mountainTags)):
			elev = mySoup.find('th',string =mountainTags[i])
			if elev is not None:
				#scrape the data next in the table
				partString = elev.find_next_sibling('td')
				if partString!=None:
					scrapedData[1] = stripString(partString.text)
					if len(scrapedData[1].strip())<=0:
						#no input for elevation
						return []
				else:
					return []


	if pageType is "Bridge":
		for i in range(len(bridgeTags)):
			elev = mySoup.find('th',string =bridgeTags[i])
			if elev is not None:

				partString = elev.find_next_sibling('td')
				if partString!=None:
					scrapedData[1] = stripString(partString.text)
					if len(scrapedData[1].strip())<=0:
						return []
				else:
					return []


	if pageType is "Building":

		#exclude nonexistant buildings
		for i in range(len(excludeTags)):
			if mySoup.find('th',string =excludeTags[i]) is not None:
				return []

		#exlcude planned buildings
		status = mySoup.find('th',string ='Status')
		if status is not None:
			partString = status.find_next_sibling('td')
			if partString is not None:
				for i in range(len(plannedTags)):
					if plannedTags[i] in partString:
						return []


		elev = None
		#find the tag with height information
		for i in range(len(buildingTags)):
			if elev is None:
				elev = mySoup.find('th',string =buildingTags[i])

		if elev is None:
			#if no height then its not a building
			return []
		else:
			#scrape the data next in the table
			partString = elev.find_next_sibling('td')
			if partString!=None:
				scrapedData[1] = stripString(partString.text)
				if len(scrapedData[1].strip())<=0:
					#no input for elevation
					return []
			else:
				return []

	if pageType is None:
		return []

	if "No size" in scrapedData[1]:
		return []

	para = mySoup.find('p')

	while para != None:

		if re.sub("\W","",mtnName) in re.sub("\W","",para.text):
			scrapedData[7] = re.sub("\[(\d*)\]","",para.text)
			break
		para = para.find_next_sibling('p')

	#find the tag with location
	loc = mySoup.find('th',string ='Location')
	if loc is not None:
		#scrape the data next in the table
		if loc.find_next_sibling('td') is not None:
			scrapedData[2] = stripString(loc.find_next_sibling('td').text)
	else:
		loc = mySoup.find('th',string ='Locale')
		if loc is not None:
			if loc.find_next_sibling('td') is not None:
				scrapedData[2] = stripString(loc.find_next_sibling('td').text)

	#find the tag with latitude
	lat = mySoup.find(class_ ='latitude')
	if lat is not None:
		#scrape the text data from it
		scrapedData[3] = lat.text

	#find the tag with longitude
	lon = mySoup.find(class_ ='longitude')
	if lon is not None:
		#scrape the text data from it
		scrapedData[4] = lon.text

	#find the og:image property
	image = mySoup.find(property = 'og:image')
	if image is not None:
		#scrape the content data from it
		scrapedData[5] = image['content']

	scrapedData[6] = pageType

	return scrapedData

def getLinksFromPage(link):
	linkList = []
	wiki = "https://en.wikipedia.org/w/api.php?"
	wikiURL = queryWikiURL(wiki, link)+setProp('links')+'pllimit=500'
	apiContinue = " "

	while (len(apiContinue)>0):

		print("Visit " + wikiURL)
		rawPage = getPage(wikiURL)
		root = etree.fromstring(rawPage.content)
		strip_ns(root)

		apiContinue = root.xpath('/api/continue/@plcontinue')
		links = root.xpath('/api/query/pages/page/links/pl/@title')

		for i in range(0,len(links)):
			#add page name to list
			if 'Geography of' not in links[i]:
				linkList.append(links[i])

		if(len(apiContinue)>0):
			#add continue api to link
			wikiURL = queryWikiURL(wiki, link)+setProp('links')+'pllimit=500&plcontinue='+apiContinue[0]

	return linkList

def getBridgeLinksFromPage(link):
	linkList = []
	wiki = "https://en.wikipedia.org/w/api.php?"
	wikiURL = queryWikiURL(wiki, link)+setProp('links')+'pllimit=500'
	apiContinue = " "
	uniqueLinks = {}

	while (len(apiContinue)>0):

		print("Visit " + wikiURL)
		rawPage = getPage(wikiURL)
		root = etree.fromstring(rawPage.content)
		strip_ns(root)

		apiContinue = root.xpath('/api/continue/@plcontinue')
		links = root.xpath('/api/query/pages/page/links/pl/@title')

		for i in range(0,len(links)):

			if 'List of bridges in ' in links[i]:
				newLinks = getLinksFromPage([links[i]])

				for x in range(len(newLinks)):
					if "Bridge" in newLinks[x] and uniqueLinks.get(newLinks[x])==None:
						linkList.append(newLinks[x])
						uniqueLinks[newLinks[x]]=1
			else:
				if "Bridge" in links[i] and uniqueLinks.get(links[i])==None:
					linkList.append(links[i])
					uniqueLinks[links[i]]=1

		if(len(apiContinue)>0):
			#add continue api to link
			wikiURL = queryWikiURL(wiki, link)+setProp('links')+'pllimit=500&plcontinue='+apiContinue[0]

	return linkList

def main():
	#how many tuples to be put in the database
	maxTuples = 10000

	mountainLinks = ['List of mountains by elevation']
	bridgeLinks = ['List_of_bridges']
	buildingLinks = ['List_of_tallest_buildings_in_Asia','List_of_tallest_buildings_in_the_United_States','List_of_tallest_buildings_in_Europe','List_of_tallest_buildings_in_Oceania','List_of_tallest_buildings_in_South_America','List_of_tallest_buildings_in_Africa']

	linkList = []
	uniqueNames = {}

	print("Getting links")
	
	potentialMountains = getLinksFromPage(mountainLinks)
	potentialBridges = getBridgeLinksFromPage(bridgeLinks)
	potentialBuildings = getLinksFromPage(buildingLinks)

	linkList = potentialMountains + potentialBridges + potentialBuildings

	mountainsSize = len(potentialMountains)
	bridgesSize = len(potentialBridges)
	buildingsSize = len(potentialBuildings)

	print("Potential links found " + str(len(linkList)))

	startIndex = 0;

	currentData = []

	if STARTNEW==False:
		with open('fullDatabase.csv') as f:
			csvreader = csv.reader(f)
			for row in csvreader:
				currentData.append(row)
				uniqueNames[row[0]]=1
				startIndex = startIndex + 1


	#open database.csv		
	with open('fullDatabase.csv','w') as f:
		#create csv writer object
		csvwriter = csv.writer(f)

		print("Getting data from individual pages")

		tuplesAcquired = 0
		for i in range(len(linkList)):
			if i>=startIndex:
				#stop if we have enough tuples
				if tuplesAcquired>=maxTuples:
					#stop when enough tuples added
					i = range(len(linkList))
				else:

					if "List of" not in linkList[i] and "Template" not in linkList[i] and "Category" not in linkList[i]:
						#create url
						pageURL = "https://en.wikipedia.org/wiki/"+linkList[i]
						print("Scraping "+pageURL)

						pageType = None
						if i < mountainsSize:
							pageType = "Mountain"
						elif i < bridgesSize:
							pageType = "Bridge"
						else:
							pageType = "Building"

						#get scraped data in list form
						pageData = scrapePage(pageURL,pageType)
							
						if len(pageData)>0:
							if uniqueNames.get(pageData[0])==None:
								#write whats in the array to the next empty row
								tuplesAcquired = tuplesAcquired + 1
								csvwriter.writerow(pageData)
								uniqueNames[pageData[0]]=1
			else:
				csvwriter.writerow(currentData[i])
				uniqueNames[currentData[i][0]]=1

	print("Finished and made "+str(tuplesAcquired)+" tuples!")

if __name__ == '__main__':
	main()
