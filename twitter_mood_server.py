from __future__ import division
from urlparse import urlparse
from flask import Flask
from collections import Iterable
from flask import make_response, request, current_app
from functools import update_wrapper
import pymysql
import json
import os
import colorsys
import datetime
import shapefile


app = Flask(__name__)
app.debug = True

db = urlparse(os.environ['DATABASE_URL'])

mood_lag = 30
sf = shapefile.Reader("states.shp")

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, datetime.timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Content-Type'] = "application/json"
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

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
@crossdomain(origin='*')
def mood():
	return calculateMood(mode="color")
	
