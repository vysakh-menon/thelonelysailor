from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)
from werkzeug.exceptions import abort
import requests
import json
from collections import namedtuple
import math
from datetime import datetime

from lsailor.db import get_db, get_db_for_scheduler
import psycopg2.extras

bp = Blueprint('message', __name__)

@bp.route('/')
@bp.route('/<admin>')
def index(admin = None):
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.NamedTupleCursor)

    cur.execute(
        'SELECT m.id, m.messagetype, m.latitude, m.longitude, CASE WHEN m.comments IS NULL THEN 0 ELSE 1 END AS hascomments'
        ' FROM DeviceMessage m WHERE m.messengerid=\'0-3131354\''
        ' ORDER BY m.id')
    device1 = cur.fetchall()

    cur.execute(
        'SELECT m.id, m.messagetype, m.latitude, m.longitude, CASE WHEN m.comments IS NULL THEN 0 ELSE 1 END AS hascomments'
        ' FROM DeviceMessage m WHERE m.messengerid=\'0-3125923\''
        ' ORDER BY m.id')
    device2 = cur.fetchall()
    cur.close()

    if admin == 'admin':
        return render_template('message/admin.html', device1 = device1, device2 = device2)
    else:
        return render_template('message/index.html', device1 = device1, device2 = device2)

@bp.route('/<int:id>/location')
def getLocation(id):

    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.NamedTupleCursor)

    cur.execute(
        'SELECT m.id, m.messengerid, m.messengername, m.unixtime, m.messagetype, m.latitude, m.longitude, m.modelid, m.showcustommsg, m.datetime, m.batterystate, m.hidden, m.altitude, m.comments, m.kph'
        ' FROM DeviceMessage m '
        ' WHERE m.id = %s', [id])
    message = cur.fetchone()
    cur.close()
    
    formatedDatetime = datetime.strptime(message.datetime, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S %Z')
    result = {}
    result['m'] = message
    result['datetime'] = formatedDatetime

    popup = render_template('message/_popupDetails.html', message=result)
    return popup

@bp.route('/<int:id>/comments')
def getComments(id):

    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.NamedTupleCursor)

    cur.execute(
        'SELECT m.id, m.comments'
        ' FROM DeviceMessage m '
        ' WHERE m.id = %s', [id])
    message = cur.fetchone()
    cur.close()

    popup = render_template('message/_popupAddComments.html', message=message)
    return popup

@bp.route('/<int:id>/save-comments', methods=["POST"])
def saveComments(id):
    comment = request.form.get('comments')
    comment = None if comment.isspace() or comment == '' else comment 
    db = get_db()
    cur = db.cursor()

    cur.execute('UPDATE DeviceMessage SET comments = %s WHERE id = %s', [comment, id])
    db.commit()
    cur.close()
    return 'success'

def fetchFromFindMeSpot(app):
    req = requests.get('https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/0NipFFigbyZRDos3T1DbG8QqeHyJWU01G/message.json')

    x = json.loads(req.text, object_hook=lambda d: namedtuple('X', d.keys(), rename=True)(*d.values()))
    if hasattr(x.response, 'feedMessageResponse'):
        query = ''

        for m in x.response.feedMessageResponse.messages.message:
            query +=  ("INSERT INTO DeviceMessage (id, messengerid, messengername, unixtime, messagetype, latitude, longitude, modelid, showcustommsg, datetime, batterystate, hidden, altitude)"
            " VALUES ({0}, '{1}', '{2}', {3}, '{4}', {5}, {6}, '{7}', '{8}', '{9}', '{10}', '{11}', '{12}') ON CONFLICT (id) DO NOTHING;"
            ).format(m.id, m.messengerId, m.messengerName, m.unixTime, m.messageType, m.latitude, m.longitude, m.modelId, m.showCustomMsg, m.dateTime, m.batteryState, m.hidden, m.altitude)
            
        with app.app_context():
            db = get_db_for_scheduler()
            cur = db.cursor()
            cur.execute(query)
            db.commit()
            cur.close()
            db.close()

        updateKPH(app)

def updateKPH(app):
    with app.app_context():
        db = get_db_for_scheduler()
        cur = db.cursor(cursor_factory = psycopg2.extras.NamedTupleCursor)

        cur.execute(
            "SELECT m.id, m.messengerid, m.latitude, m.longitude, m.datetime"
            " FROM DeviceMessage m WHERE m.kph is null ORDER BY m.id")
        messages = cur.fetchall()

        previous = {}
        query = ''
        for m in messages:
            if previous.get(m.messengerid) is None:
                previous[m.messengerid] = getLastMessage(m.id, m.messengerid, app)
            
            kph = '0' if previous.get(m.messengerid) is None else calculateKPH(previous[m.messengerid], m)

            query +=  ("UPDATE DeviceMessage SET kph = {0} WHERE id = {1};").format(kph, m.id)
                    
            previous[m.messengerid] = {}
            previous[m.messengerid]['latitude'] = m.latitude
            previous[m.messengerid]['longitude'] = m.longitude
            previous[m.messengerid]['datetime'] = m.datetime

        if query != '':
            cur.execute(query)
            db.commit()

        cur.close()
        db.close()

def getLastMessage(id, messengerId, app):
    with app.app_context():
        db = get_db_for_scheduler()
        cur = db.cursor(cursor_factory = psycopg2.extras.NamedTupleCursor)

        cur.execute(
            'SELECT m.latitude, m.longitude, m.datetime'
            ' FROM DeviceMessage m'
            ' WHERE m.messengerid = %s AND m.id < %s'
            ' ORDER BY m.id DESC', [messengerId, id])
        row = cur.fetchone()
        cur.close()
        db.close()

        if row is not None:
            message = {}
            message['latitude'] = row.latitude
            message['longitude'] = row.longitude
            message['datetime'] = row.datetime
            return message
        else:
            return None

def calculateKPH(previous, current):
    dist = distanceOnGeo(previous['latitude'], previous['longitude'], current.latitude, current.longitude)
    previousDate = datetime.strptime(previous['datetime'], '%Y-%m-%dT%H:%M:%S%z')
    currentDate = datetime.strptime(current.datetime, '%Y-%m-%dT%H:%M:%S%z')
    time_s = (currentDate - previousDate).total_seconds()
    speed_mps = dist / time_s
    speed_kph = (speed_mps * 3600.0) / 1000.0
    return round(abs(speed_kph), 2)

def distanceOnGeo(lat1, lon1, lat2, lon2):
    #Convert degrees to radians
    lat1 = float(lat1) * math.pi / 180.0
    lon1 = float(lon1) * math.pi / 180.0

    lat2 = float(lat2) * math.pi / 180.0
    lon2 = float(lon2) * math.pi / 180.0

	#radius of earth in metres
    r = 6378100

	#P
    rho1 = r * math.cos(lat1)
    z1 = r * math.sin(lat1)
    x1 = rho1 * math.cos(lon1)
    y1 = rho1 * math.sin(lon1)

	#Q
    rho2 = r * math.cos(lat2)
    z2 = r * math.sin(lat2)
    x2 = rho2 * math.cos(lon2)
    y2 = rho2 * math.sin(lon2)

	#Dot product
    dot = (x1 * x2 + y1 * y2 + z1 * z2)
    cos_theta = dot / (r * r)

    theta = math.acos(cos_theta)

	#Distance in Metres
    return r * theta
