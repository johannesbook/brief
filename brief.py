# -*- coding: utf-8 -*-

#Todo
# surfstatus - om närmsta veckan visa en ruta med detaljer
# kyleffekt
# risk för åska
# tågtider och förseningar
# visa inte badtunnetemp om vi inte eldar
# fält för text - typ "regn idag", eller "tågen sena!"
# felhantering - vad om något av api'n inte svarar? 

#####
### Hack to display some status on 7" tablet next to entrance
#####

import re
from robobrowser import RoboBrowser
from datetime import datetime
from datetime import timedelta
import locale
import time
import requests
import json
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

while True:
	
	###
	### Accessing thinger.io API to get badtunnetemp
	###
	print str(datetime.now()) + ": Accessing thinger.io..."
	url = 'https://api.thinger.io/v2/users/johannesbook/devices/badtunnecontroller/temp1'
	headers = {'content-type': 'application/json, text/plain, */*', \
        	'Authorization': 'Bearer keygoeshere'}
	r = requests.get(url, headers=headers)
	if r.text == "{\"error\":{\"message\":\"device not found\"}}": #if wifi of the arduino has hung and needs reboot
		thingerBadtunneTemp = -99
	else:
		thingerBadtunneTemp = json.loads(r.text)['out']

	###
	### Nibe Uplink scraping - data from house heater
	###
	print str(datetime.now()) + ": Accessing Nibe Uplink..."
	browser = RoboBrowser(history=True, parser='html.parser')
	browser.open('http://www.nibeuplink.com/')
	form = browser.get_form(action='/LogIn')
	form["Email"] = 'email'
	form["Password"] = 'pwd'
	browser.submit_form(form)
	browser.open('https://www.nibeuplink.com/System/38188/Status/ServiceInfo')
	html = str(browser.select)

	nibeOutTemp = re.search(r'.*utetemperatur.*?>([-?\d\.]*)\\xb0C',html).group(1) 
	nibeWaterTempTop = re.search(r'.*varmvatten.*?topp.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeWaterTempBot = re.search(r'.*varmvatten.*?laddning.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeExhaustTemp = re.search(r'.*avluft.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeRoomTemp = re.search(r'.*rumstemperatur.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeHeatOut = re.search(r'.*framledningstemp.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeHeatReturn = re.search(r'.*retur\.temp.*?>([\d\.]*)\\xb0C',html).group(1) 
	nibeHeaterPower = re.search(r'.*effekt.eltillsats.*?>([\d\.]*)kW',html).group(1) 

	nibeWaterSOC = 100 * (((float(nibeWaterTempTop) + float(nibeWaterTempBot)) / 2) - 38 ) / (49-38)  # 38 degrees = minimum comfort. 49 degress = 100%. 
	if nibeWaterSOC > 98 and nibeWaterSOC < 102 :
		nibeWaterSOC = 100	#disregard of natural fluctuations (heater hysteresis)
		
	###
	### Weather data
	###
	print str(datetime.now()) + ": Accessing SMHI API..."
	lat = '55.365' #~Kattingvagen, Trelleborg
	lon = '13.225'

	url = 'https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/' + lon + '/lat/' + lat + '/data.json'
	r = requests.get(url)
	forecast = json.loads(r.text)
	
	#calculate how much precipitation that remains today
	hourNow = int(datetime.now().strftime('%H'))
	remainingHours = 24 - hourNow + 1
	remainingPrecipitation = 0
	for i in range(1,remainingHours):
		for j in range (0,18):	#there are 19 parameters in the API
			if forecast['timeSeries'][i]['parameters'][j]['name'] == 'pmean': #pmean is the hourly average precipitation
				remainingPrecipitation += float(forecast['timeSeries'][i]['parameters'][j]['values'][0])
	if remainingPrecipitation == 0:
		remainingPrecipitation = "0" #if 0.0 print 0...
	else:
		remainingPrecipitation = str(remainingPrecipitation) #but if i.e. 0.1, print 0.1
		
	#check wind now
	for j in range (0,18):
		if forecast['timeSeries'][0]['parameters'][j]['name'] == 'ws':
			windSpeedNow = forecast['timeSeries'][0]['parameters'][j]['values'][0]
		if forecast['timeSeries'][0]['parameters'][j]['name'] == 'wd':
			windDirNow = forecast['timeSeries'][0]['parameters'][j]['values'][0]

	windDirections = ["nord","nordnordost","nordost","ostnordost","ost","ostsydost","sydost","sydsydost","syd","sydsydväst","sydväst","västsydväst","väst","västnordväst","nordväst","nordnordväst","nord"]
	windDirIndex = int(round((windDirNow % 360) / 22.5,0) )

	#Calculate windchill, based on temperature and wind
	windChill = 13.12 + 0.625*float(nibeOutTemp) - 13.956*float(windSpeedNow)**0.16 + 0.48669*float(nibeOutTemp)*float(windSpeedNow)**0.16
	
	###
	### Get namnsdag
	###
	print str(datetime.now()) + ": Accessing dagensnamn.nu..."
	browser = RoboBrowser(history=True, parser='html.parser')
	browser.open('https://www.dagensnamn.nu/')
	html = str(browser.select)
	namnsDag = re.search(r'.*har</h3><h1 style="margin-bottom:20px;">(.*)</h1><h3 style="margin-top:0px;">....namnsdag.',html).group(1) 
	if (datetime.today().day == 25 and datetime.today().month == 2): 
		namnsDag += ", Elvin"
	
	###
	### Get calendar events
	###
	
	print str(datetime.now()) + ": Accessing Google calendar API..."
	SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
	store = file.Storage('/home/pi/brief/token.json')
	creds = store.get()
	if not creds or creds.invalid:
		flow = client.flow_from_clientsecrets('/home/pi/brief/credentials.json', SCOPES)
		creds = tools.run_flow(flow, store)
	service = build('calendar', 'v3', http=creds.authorize(Http()))

    #Call the Calendar API
	now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
	events_result = service.events().list(calendarId='email', timeMin=now,
										maxResults=20, singleEvents=True,
                                        orderBy='startTime').execute()
	events = events_result.get('items', [])

	calToday = ''
	calTomorrow = ''
	calDayAfterTomorrow = ''
	if not events:
		calToday = 'Tomt i kalendern!'
	for event in events:
		start = event['start'].get('dateTime', event['start'].get('date'))
		#print start
		if 'T' in start:
			start = re.sub('\+01:00','',start) #remove time zone info - not interesting
			start = datetime.strptime(start,'%Y-%m-%dT%H:%M:%S')
		else:
			start = datetime.strptime(start,'%Y-%m-%d')
		
		if start.day == datetime.now().day:
			#calToday += 'Idag'
			if not (start.hour == 0 and start.minute == 0): #not full day event
				calToday += ' ' + str(start.hour).zfill(2) + ':' + str(start.minute).zfill(2) + ': '
			calToday += event['summary'].encode('utf-8')
			calToday += '<br/>'	

		if start.day == (datetime.now() + timedelta(days=1)).day:
			if not (start.hour == 0 and start.minute == 0): #not full day event
				calTomorrow += ' ' + str(start.hour).zfill(2) + ':' + str(start.minute).zfill(2) + ': '
			calTomorrow += event['summary'].encode('utf-8')
			calTomorrow += '<br/>'	

		if start.day == (datetime.now() + timedelta(days=2)).day:
			if not (start.hour == 0 and start.minute == 0): #not full day event
				calDayAfterTomorrow += ' ' + str(start.hour).zfill(2) + ':' + str(start.minute).zfill(2) + ': '
			calDayAfterTomorrow += event['summary'].encode('utf-8')
			calDayAfterTomorrow += '<br/>'	
			
	if calTomorrow == '':
		calTomorrow += 'Inget!'
	if calDayAfterTomorrow == '':
		calDayAfterTomorrow += 'Inget!'
			

			#if start.day == (datetime.now() + timedelta(days=1)).day:
		#	cal += 'Imorgon'
		#	else: 
		#		if start.day == (datetime.now() + timedelta(days=2)).day:
		#			cal += 'I övermorgon ' #hrmpf
		#		else:
		#			cal += str(start)
		
		#if start.day == datetime.now().day or start.day == (datetime.now() + timedelta(days=1)).day: #if not today or tomorrow, skip
		#	if start.hour == 0 and start.minute == 0: #full day event
		#		cal += ': '
		#	else:
		#		cal += ' ' + str(start.hour).zfill(2) + ':' + str(start.minute).zfill(2) + ': '
		#	cal += event['summary'].encode('utf-8')
		#	cal += '<br/>'	
		
	###
	### Get time
	###
	print str(datetime.now()) + ": Getting local time..."
	locale.setlocale(locale.LC_ALL, 'sv_SE.utf8')
	clock = datetime.now().strftime('%H:%M')
	date = str(datetime.now().strftime('%A %d:e %B'))
	
	###
	### Top message
	###
	topMessage = ''
	if hourNow >= 0 and hourNow < 6:
		topMessage = 'Natt'
	if hourNow >= 6 and hourNow < 9:
		topMessage = 'Godmorgon!'
	if hourNow >= 9 and hourNow < 12:
		topMessage = 'God förmiddag!'
	if hourNow >= 12 and hourNow < 17:
		topMessage = 'God eftermiddag!'
	if hourNow >= 17:
		topMessage = 'Godkväll!'
	if windSpeedNow > 14:
		topMessage = 'Kuling ute'
	if float(nibeOutTemp) < 0: 
		topMessage = 'Frost ute'
	if windSpeedNow > 24:
		topMessage = 'Storm ute'
	if (datetime.today().day == 25 and datetime.today().month == 2): 
		topMessage = 'Grattis på namnsdagen Elvin!'
	if (datetime.today().day == 16 and datetime.today().month == 3): 
		topMessage = 'Grattis på födelsedagen Elvin!'
	if (datetime.today().day == 24 and datetime.today().month == 12): 
		topMessage = 'God jul!'
	if (datetime.today().day == 3 and datetime.today().month == 3): 
		topMessage = 'Grattis på födelsedagen Jenny!'
	if (datetime.today().day == 13 and datetime.today().month == 11): 
		topMessage = 'Grattis på födelsedagen Sixten!'
	if (datetime.today().day == 27 and datetime.today().month == 6): 
		topMessage = 'Grattis på födelsedagen Johannes!'


	###
	### Create HTML file
	###
	print str(datetime.now()) + ": Printing HTML file..."
	htmlout = """
	<html>
		<head>
			<link rel="stylesheet" href="stylesheet.css" type="text/css" />
			<link href="https://fonts.googleapis.com/css?family=Open+Sans:300" rel="stylesheet">
			<link href='https://fonts.googleapis.com/css?family=EB+Garamond' rel='stylesheet' type='text/css'>
			<link href='https://fonts.googleapis.com/css?family=Lobster' rel='stylesheet' type='text/css'>
			<meta http-equiv="Cache-control" content="No-Cache">
			<meta charset="utf-8" />
			<meta http-equiv="refresh" content="61" />
			<title>Brief</title>
		</head>
		<body>
			<div id='sub'>
				<div id='top-box'>
					<span id='top'>""" + topMessage + """</span>
				</div>
			</div>
			<div id='sub'>
				<div id='box'>
					<span id='big'>""" + clock + """<br/></span>
					<span id='small'>""" + date + """<br/>""" + namnsDag + """</span>
				</div>
				<div id='box'>
					<span id="big">""" + str(round(float(nibeOutTemp),0)).rstrip('0').rstrip('.') + """°<br/></span>
					<span id="small">..just nu. """ + str(round(float(windSpeedNow),0)).rstrip('0').rstrip('.') + """m/s, """ + windDirections[windDirIndex] + """<br/>
					  känns som """ + str(round(windChill,0)).rstrip('0').rstrip('.') + """°
					</span>
				</div>
				<div id='box'>
					<span id="big">""" +  str(round(float(nibeRoomTemp),0)).rstrip('0').rstrip('.') + """°<br/></span>
					<span id="small">..inne, """ + str(round(float(nibeWaterSOC),0)).rstrip('0').rstrip('.') + """% värme i pannan, <br/>
					  """ + str(round(float(thingerBadtunneTemp),0)).rstrip('0').rstrip('.') + """° i badtunnan<br/></span>
				</div>
			</div>
			<div id='sub'>
				<div id='box'>
					<span id="cal">""" 
	if calToday != '':
		htmlout += """Idag: <br/>""" + calToday + """<br/> """
	htmlout += """Imorgon: <br/>""" + calTomorrow + """</span>
					<!--- <span id="cal">Imorgon: <br/>""" + calTomorrow + """</span>--->
				</div>
				<div id='box'>
					<span id="big">""" + remainingPrecipitation + """<br/></span>
					<span id="small">..mm regn under resten av dagen</span>
				</div>
				<div id='box'>
				</div>
			</div>
	<!---		<div id='foot'>
				<span id='small'>brief by Johannes Book 2018&nbsp;&nbsp;</span>
			</div>--->
		</body>
	</html>
	"""

	with open('/var/www/html/brief.html', 'w') as file:
		file.write(htmlout)
		
	print str(datetime.now()) + ": Sleeping..."
	time.sleep(5)
	
