# -*- coding: utf-8 -*-
from flask import Flask, render_template, url_for, request
import csv
import sys
from math import sin, cos, sqrt, atan2, radians, ceil

import whoosh
from whoosh import index
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser

app = Flask(__name__)

#127.0.0.1:5000
#FLASK_APP=landmarkAttractions.py flask run

def sanitizeInput(input):

	return re.sub(r'[^0-9A-Za-z\s]+','',input)

def degreesMinutesSecondsToDec(dms):

	if re.search(r'\d+″',dms.encode('utf8')) is None:
		return None

	degrees = float(re.search(r'\d+',dms.encode('utf8')).group(0))
	minutes = re.search(r'°\d+',dms.encode('utf8')).group(0)
	seconds = re.search(r'′\d+',dms.encode('utf8')).group(0)

	minutes = float(re.sub('°','',minutes))
	seconds = float(re.sub('′','',seconds))

	dd = degrees + minutes/60 + seconds/3600

	if "W" in dms:
		dd = -1*dd
	if "S" in dms:
		dd = -1*dd


	return dd

def distanceBetweenCoords(lon1,lat1, lat2, lon2):

	if lon2 == None or lat2 == None:
		return -1

	#convert to radians
	lat1 = radians(lat1)
	lat2 = radians(lat2)
	lon1 = radians(lon1)
	lon2 = radians(lon2)

	radius = 3959#miles
	haversine = (sin((lat2-lat1)/2)**2 )+ (cos(lat1)*cos(lat2)*(sin((lon2-lon1)/2)**2))
	dist = radius*2*atan2(sqrt(haversine),sqrt(1-haversine))

	return dist

@app.route('/', methods=['GET', 'POST'])
def index():
	return render_template('homePage.html')

@app.route('/results/', methods=['GET', 'POST'])
def results():

	global indexer
	if request.method == 'POST':
		data = request.form
	else:
		data = request.args

	#get all of the input data
	keywordquery = sanitizeInput(data.get('searchterm'))
	lat = float(data.get('latitude'))
	lon = float(data.get('longitude'))
	searchType = data.get('type')
	page = int(data.get('page'))
	searchRange = data.get('range')
	searchRange = re.sub(r'[^0-9]+','',searchRange)

	if len(searchRange)==0:
		searchRange = -1
	else:
		searchRange = int(searchRange)

	maxResultsPerPage = 10

	searchResults = search(indexer,keywordquery,searchType,searchRange, lat, lon)
	maxPage = ceil(float(len(searchResults[0]))/float(maxResultsPerPage))

	Name = list()
	Size = list()
	Location = list()
	Longitude = list() 
	Latitude= list()
	Image= list()
	Type = list()
	Description = list()
	Distance = list()

	#paginate search results
	if page<=maxPage and page>0:
		for i in range(maxResultsPerPage):
			currentResult = ((page-1)*maxResultsPerPage) + i
			if len(searchResults[0]) > currentResult:
				Name.append(searchResults[0][currentResult])
				Size.append(searchResults[1][currentResult])
				Location.append(searchResults[2][currentResult])
				Longitude.append(searchResults[3][currentResult])
				Latitude.append(searchResults[4][currentResult])
				if "No image" in searchResults[5][currentResult]:
					#no image found for this result
					Image.append("/static/noImage.png")
				else:
					Image.append(searchResults[5][currentResult])
				Type.append(searchResults[6][currentResult])
				Description.append(searchResults[7][currentResult])
				Distance.append(int(ceil(searchResults[8][currentResult])))

	return render_template('frontEnd.html', resultAmount = len(Name), maxResults = len(searchResults[0]),searchterm = keywordquery,type =searchType, range = data.get('range'), page = page, maxPage = int(maxPage), searchType = searchType, latitude= lat, longitude= lon, query=keywordquery, results=zip(Name, Size, Location, Longitude, Latitude, Image, Type, Description, Distance))

def search(indexer, searchTerm, searchType, range, lat, lon):
	Name = list()
	Size = list()
	Location = list()
	Longitude = list() 
	Latitude= list()
	Image= list()
	Type = list()
	Description = list()
	Distance = list()

	with indexer.searcher() as searcher:
		query = MultifieldParser(['Name', 'Location', 'Type','Description'], schema=indexer.schema) #Search fields in Schema
		query = query.parse(searchTerm) #Parse to find search term
		results = searcher.search(query, limit=None) #Store search results

		for x in results:

			inRange = True
			if range > -1:
				dist = distanceBetweenCoords(lat, lon, degreesMinutesSecondsToDec(x['Latitude']), degreesMinutesSecondsToDec(x['Longitude']))
				if dist>range or dist<0:
					inRange = False
			else:
				#unlimited distance
				dist = distanceBetweenCoords(lat, lon, degreesMinutesSecondsToDec(x['Latitude']), degreesMinutesSecondsToDec(x['Longitude']))
				if dist<0:
					inRange = False

			#type settings check
			if inRange == True:
				if searchType == "Any":
					Name.append(x['Name'])
					Size.append(x['Size'])
					Location.append(x['Location'])
					Longitude.append(x['Longitude'])
					Latitude.append(x['Latitude'])
					Image.append(x['Image'])
					Type.append(x['Type'])
					Description.append(x['Description'])
					Distance.append(dist)
				elif searchType in x['Type']:
					Name.append(x['Name'])
					Size.append(x['Size'])
					Location.append(x['Location'])
					Longitude.append(x['Longitude'])
					Latitude.append(x['Latitude'])
					Image.append(x['Image'])
					Type.append(x['Type'])
					Description.append(x['Description'])
					Distance.append(dist)


	return Name, Size, Location, Longitude, Latitude, Image, Type, Description, Distance


def index():
    schema = Schema(id=ID(stored=True), Name=TEXT(stored=True), Size=TEXT(stored=True), Location=TEXT(
        stored=True), Longitude=TEXT(stored=True), Latitude=TEXT(stored=True), Image=TEXT(stored=True), Type=TEXT(stored=True), Description=TEXT(stored=True)) #Schema created
    indexer = create_in('Back_End', schema) #Make sure there is a directory for the indexing method to store it's contents in  
    writer = indexer.writer() 

    csvfile = open('fullDatabase.csv', 'r')
    reader = csv.reader(csvfile, delimiter=',')
    line_count = 0
    for element in reader: 
        writer.add_document(Name=unicode(element[0], "utf-8"), Size=unicode(element[1], "utf-8"), Location=unicode(element[2], "utf-8"),
                            Longitude=unicode(element[3], "utf-8"), Latitude=unicode(element[4], "utf-8"), Image=unicode(element[5], "utf-8"), Type=unicode(element[6], "utf-8"), Description=unicode(element[7], "utf-8")) #For each line, store every element to it's respective attribute  #FIX THIS
        line_count += 1

    print("Total Tuples:", line_count)
    writer.commit()

    return indexer

indexer = index()

if __name__ == '__main__':
	app.run(debug=True)