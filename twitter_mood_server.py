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

mood_lag = 15
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

def hue2hex(hue):
	orgb = colorsys.hsv_to_rgb(hue, 1, 1)
	rgb = []
	for c in orgb:
		test = int(c * 256)
		if test == 256:
			test = test - 1
		rgb.append(test)
	hx = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])
	return hx

def calculateMood():
	global mood_lag
	if db.port:
		cnx = pymysql.connect(charset='utf8', host=db.hostname, port=db.port, user=db.username, passwd=db.password, db=db.path[1:])
	else:
		cnx = pymysql.connect(charset='utf8', host=db.hostname, user=db.username, passwd=db.password, db=db.path[1:])

	cursor = cnx.cursor()
	mood = dict()

	rs = "SELECT state, AVG(sentiment), COUNT(sentiment) FROM tweets WHERE `date` > %s GROUP BY state"
	lag = datetime.datetime.now() - datetime.timedelta(minutes=mood_lag)
	params = [lag.isoformat(' ')]
	cursor.execute(rs, params)
	
	for st in sf.shapeRecords():
		mood[st.record[31]]['sentiment'] = 0

	for state, sentiment, count in cursor:
		if state in mood:
			mood[state]['sentiment'] = sentiment
			mood[state]['count'] = count

	meanQuery = "SELECT AVG(avg) FROM statistics"
	avgStat = 0
	cursor.execute(statistic)
	for avg in cursor:
		avgStat = avg

	stddevQuery = "SELECT state, STDDEV(sentiment) FROM tweets GROUP BY state;"
	cursor.execute(stddevQuery)
	for state, std in cursor:
		if state in mood:
			mood[state]['std'] = std
			if std != 0:
				mood[state]['mood_score'] = (mood[state][sentiment] - avgStat)/std
				if mood[state]['mood_score'] > .6:
					hue = 120/360
				elif mood[state]['mood_score'] < -.6:
					hue = 0
				else:
					hue = (60 + (100*mood[state]['mood_score']))/360
			else:
				mood[state]['mood_score'] = 0
				hue = 60/360
			mood[state]['color'] = hue2hex(hue)

	cursor.close()
	cnx.close()
	
	return json.dumps(mood)

@app.route('/')
@crossdomain(origin='*')
def mood():
	return calculateMood()
	
