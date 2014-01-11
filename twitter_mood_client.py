from __future__ import division
from urlparse import urlparse
from flask import Flask
from collections import Iterable
import pymysql
import json
import os
import colorsys
import datetime
import shapefile


app = Flask(__name__)
app.debug = True

db = urlparse(os.environ['DATABASE_URL'])

mood_lag = 15
sf = shapefile.Reader("states.shp")

def calculateMood(mode):
	global mood_lag
	if db.port:
		cnx = pymysql.connect(charset='utf8', host=db.hostname, port=db.port, user=db.username, passwd=db.password, db=db.path[1:])
	else:
		cnx = pymysql.connect(charset='utf8', host=db.hostname, user=db.username, passwd=db.password, db=db.path[1:])

	cursor = cnx.cursor()
	sentimentDict = dict()
	countDict = dict()
	colorDict = dict()
	avgDict = dict()
	rs = "SELECT state, sentiment FROM tweets WHERE `date` > %s"
	lag = datetime.datetime.now() - datetime.timedelta(minutes=mood_lag)
	params = [lag.isoformat(' ')]
	cursor.execute(rs, params)
	
	for st in sf.shapeRecords():
		sentimentDict[st.record[31]] = 0
		countDict[st.record[31]] = 0

	for state, sentiment in cursor:
		if state in sentimentDict:
			sentimentDict[state] += sentiment
			countDict[state] += 1

	for state, sen in sentimentDict.iteritems():
		if countDict[state] != 0:
			avg = sen/countDict[state]
			avgDict[state] = avg
			if avg > 0:
				sign = 1
			else:
				sign = -1
			hue = (60 + 60*sign*pow(abs(avg), (1/2.3)))/360
		else:
			hue = 60/360
		orgb = colorsys.hsv_to_rgb(hue, 1, 1)
		rgb = []
		for c in orgb:
			test = int(c * 256)
			if test == 256:
				test = test - 1
			rgb.append(test)
		hx = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])
		colorDict[state] = hx

	cursor.close()
	cnx.close()
	
	if mode == "count":
		return json.dumps(countDict)

	elif mode == "color":
		return json.dumps(colorDict)

	else:
		return json.dumps(avgDict)

@app.route('/')
def mood():
	return calculateMood(mode="color")
	
