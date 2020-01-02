# -*- coding: utf-8 -*-

#Todo
# visa diff mellan nutid och senaste omladdningstid (health.js?)
# visa vädret bättre (pil och sånt, och visa nu och sen på samma vis)
# tågtider och förseningar
# surfstatus - om närmsta veckan visa en ruta med detaljer
# risk för åska, hagel och sånt
# felhantering - vad om något av api'n inte svarar? 
# api play nice - fråga inte smhi vid varje reload etc.

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
from bs4 import BeautifulSoup
import urllib2
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

while True:
	
	###
	### Checking train delays with skånetrafiken
	###
	
	url = 'http://www.labs.skanetrafiken.se/v2.2/resultspage.asp?cmdaction=previous&selPointFr=malm%F6%20C|80000|0&selPointTo=trelleborg|87071|0'
	file2 = urllib2.urlopen(url)
	data = file2.read()
	file2.close()

	
	# root = ET.fromstring(data)
	
	# for journeys in root[0][0][0][3]:
		# for journey in journeys[13]:
			# departure = journey[1].text
			# depdev = journey[7][0][2].text
			# arrival = journey[3].text
			# arrdev = journey[7][0][4].text
			# if arrdev != "0":
				# devString = "FIXA HÄR TYP 22.20 avgick 3 minuter sent"
			# print "dep: ", departure
			# print "dep dev: ", depdev
			# print "arr: ", arrival
			# print "arrdev: ", arrdev
			#kolla också hur cancelleringar syns
	
	# break
	
	###
	### Accessing thinger.io API to get badtunnetemp
	###
	print str(datetime.now()) + ": Accessing thinger.io..."
	url = 'https://api.thinger.io/v2/users/johannesbook/devices/badtunnecontroller/temp1'
	headers = {'content-type': 'application/json, text/plain, */*', \
        	'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJicmllZiIsInVzciI6ImpvaGFubmVzYm9vayJ9.Nxh_5BsFNRS10GJToEC-q_4Ii1lJGLPUJq8YNNd8sSk'}
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
	print "..2.."
	form = browser.get_form(action='/LogIn')
	form["Email"] = 'email'
	form["Password"] = 'pass'
	browser.submit_form(form)
	print "..3.."
	browser.open('https://www.nibeuplink.com/System/38188/Status/ServiceInfo')
	html = str(browser.select)
	print "..4.."

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
	windDirIndexNow = int(round((windDirNow % 360) / 22.5,0) )

	#Calculate windchill, based on temperature and wind
	windChill = 13.12 + 0.625*float(nibeOutTemp) - 13.956*float(windSpeedNow)**0.16 + 0.48669*float(nibeOutTemp)*float(windSpeedNow)**0.16

	###
	### Check forcast for next morning / evening - next potential bikeride
	###
	targetHour = 6
	if hourNow >= 5:
		targetHour = 18
	if hourNow >= 18:
		targetHour = 6
	hourDelta = targetHour - hourNow #how many hours from now should we check
	if hourDelta < 0: 
		hourDelta = hourDelta + 24
		
	#wind and wind dir
	for j in range (0,18):
		if forecast['timeSeries'][hourDelta]['parameters'][j]['name'] == 'ws':
			windSpeedThen = forecast['timeSeries'][hourDelta]['parameters'][j]['values'][0]
		if forecast['timeSeries'][hourDelta]['parameters'][j]['name'] == 'wd':
			windDirThen = forecast['timeSeries'][hourDelta]['parameters'][j]['values'][0]
	windDirIndexThen = int(round((windDirNow % 360) / 22.5,0) )

	#precipitation
	for j in range (0,18):	#there are 19 parameters in the API
		if forecast['timeSeries'][hourDelta]['parameters'][j]['name'] == 'pmean': #pmean is the hourly average precipitation
			precipitationThen = float(forecast['timeSeries'][hourDelta]['parameters'][j]['values'][0])

	#precipitation type
	for j in range (0,18):	#there are 19 parameters in the API
		if forecast['timeSeries'][hourDelta]['parameters'][j]['name'] == 'pcat': #category
			precipitationCategoryThen = float(forecast['timeSeries'][hourDelta]['parameters'][j]['values'][0])

	#temperature
	for j in range (0,18):	#there are 19 parameters in the API
		if forecast['timeSeries'][hourDelta]['parameters'][j]['name'] == 't': #temp 
			tempThen = float(forecast['timeSeries'][hourDelta]['parameters'][j]['values'][0])
	
	###
	### Get namnsdag
	###
	print str(datetime.now()) + ": Accessing dagensnamn.nu..."
	browser = RoboBrowser(history=True, parser='html.parser')
	browser.open('https://www.dagensnamn.nu/')
	html = str(browser.select)
	namnsDag = re.search(r'.*har</span></div><h1>(.*)</h1><div class="today">....namnsdag.',html)
	#namnsDag = re.search(r'.*har</h3><h1 style="margin-bottom:20px;">(.*)</h1><h3 style="margin-top:0px;">....namnsdag.',html)
	if namnsDag:
		namnsDag = namnsDag.group(1)
	else:
		namnsDag = ""
	if (datetime.today().day == 25 and datetime.today().month == 2): 
		namnsDag += ", Elvin"
	
	###
	### Get calendar events
	###
	
	print str(datetime.now()) + ": Accessing Google calendar API..."
	SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
	store = file.Storage('/home/pi/brief/token.json')
	try: creds = store.get()
	except: print "aaargh"
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
			print "1" + start
			start = re.sub('\+01:00','',start) #remove time zone info - not interesting
			start = re.sub('\+02:00','',start) #could be 2 hours too, apparently. :( 
			print "2" + start
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
		calTomorrow += 'Inget i kalendern!'
	if calDayAfterTomorrow == '':
		calDayAfterTomorrow += 'Inget!'
					
	###
	### Get time
	###
	print str(datetime.now()) + ": Getting local time..."
	locale.setlocale(locale.LC_ALL, 'sv_SE.utf8')
	created = datetime.now()
	clock = datetime.now().strftime('%H:%M')
	date = str(datetime.now().strftime('%A %d:e %B'))
	
	###
	### Top message
	###
	minuteNow = datetime.now().minute

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
	if (hourNow == 7 and minuteNow >= 0 and minuteNow <= 20) or (hourNow == 6 and minuteNow >= 0 and minuteNow <= 20):
		topMessage = 'Ha en bra dag!'
	if float(remainingPrecipitation) > 1:
		topMessage = 'Nederbörd idag.'
	if float(windSpeedNow) > 14:
		topMessage = 'Kuling nu!'
	if float(nibeOutTemp) < 0: 
		topMessage = 'Frost nu!'
	if float(windSpeedNow) > 24:
		topMessage = 'Storm nu!'
	if (datetime.today().day == 25 and datetime.today().month == 2): 
		topMessage = 'Grattis på namnsdagen Elvin!'
	if (datetime.today().day == 16 and datetime.today().month == 3): 
		topMessage = 'Grattis på födelsedagen Elvin!'
	if (datetime.today().day == 17 and datetime.today().month == 3): 
		topMessage = 'Grattis på födelsedagen Sinus!'
	if (datetime.today().day == 3 and datetime.today().month == 5): 
		topMessage = 'Grattis på födelsedagen Jenny!'
	if (datetime.today().day == 27 and datetime.today().month == 6): 
		topMessage = 'Grattis på födelsedagen Johannes!'
	if (datetime.today().day == 6 and datetime.today().month == 10): 
		topMessage = 'Grattis på namnsdagen Jenny!'
	if (datetime.today().day == 13 and datetime.today().month == 11): 
		topMessage = 'Grattis på födelsedagen Sixten!'
	if (datetime.today().day == 5 and datetime.today().month == 12): 
		topMessage = 'Ha en bra studiedag Elvin!'
	if (datetime.today().day == 14 and datetime.today().month == 12): 
		topMessage = 'Grattis på namnsdagen Sixten!'
	if (datetime.today().day == 24 and datetime.today().month == 12): 
		topMessage = 'God jul!'
	if (datetime.today().day == 27 and datetime.today().month == 12): 
		topMessage = 'Grattis på namnsdagen Johannes!'
	if (datetime.today().day == 31 and datetime.today().month == 12): 
		topMessage = 'Gott nytt år!'
	if (float(thingerBadtunneTemp) - float(nibeOutTemp) > 10):
		topMessage = str(round(float(thingerBadtunneTemp),0)).rstrip('0').rstrip('.') + '° i badtunnan!'
	
	
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
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
		<script src="js/main.js"></script>
		<body onload="main()">"""
		
	if (datetime.today().day == 1 and datetime.today().month == 1): 
		htmlout +=  """	<div id='anim'><img src='https://media.giphy.com/media/uV6ZueyzR8J6pCdxtZ/giphy.gif' /></div>"""
			
	htmlout += """ 
			<div id='sub'>
						<div id='top-box'>
					<span id='top'>""" + topMessage + """</span>
				</div>
			</div>
			<div id='sub'>
				<div id='box'>
					<span id='big'><div id='jsclock'></div></span>
					<!---<span id='big'>""" + clock + """<br/></span>--->
					<span id='small'>""" + date + """<br/>""" + namnsDag + """</span>
					<span id='alert'><div id='outofdate'></div></span>
				</div>
				<div id='box'>
					<!---<span id="big">""" + str(round(float(nibeOutTemp),0)).rstrip('0').rstrip('.') + """°<br/></span>--->
					<span id="big">""" + str(round(float(windSpeedNow),0)).rstrip('0').rstrip('.')  + """ m/s<br/></span>
					<span id="small">""" + windDirections[windDirIndexNow] + """ just nu. <br/> 
						""" + str(round(float(nibeOutTemp),0)).rstrip('0').rstrip('.') + """°, känns som """ + str(round(windChill,0)).rstrip('0').rstrip('.') + """°
					</span>
					<span id="small"><div id='trainStatus'></div></span>
				</div>
				<div id='box'>
					<!---<span id="big">""" +  str(round(float(nibeRoomTemp),0)).rstrip('0').rstrip('.') + """°<br/></span> --->
					<span id="big">""" +  str(round(float(nibeOutTemp),0)).rstrip('0').rstrip('.') + """°<br/></span>
					<span id="small">utomhus<br/> """ + str(round(float(nibeRoomTemp),0)).rstrip('0').rstrip('.') + """° inne<br/>
					""" + str(round(float(nibeWaterTempTop),0)).rstrip('0').rstrip('.') + """° (""" + str(round(float(nibeWaterSOC),0)).rstrip('0').rstrip('.') + """%) i pannan<br/>
					""" + str(round(float(nibeExhaustTemp),0)).rstrip('0').rstrip('.') + """° avluftstemp<br/> 
					""" + str(round(float(nibeHeaterPower),0)).rstrip('0').rstrip('.') + """ kW elpatron<br/> 
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
					<span id="big">""" + str(round(float(windSpeedThen),0)).rstrip('0').rstrip('.') + """ m/s<br/></span>
					<span id="small">""" + windDirections[windDirIndexThen] 
	if 	targetHour == 6:
		htmlout += """ imorgon bitti, <br/>"""
	if 	targetHour == 18:
		htmlout += """ ikväll, <br/>"""
	if precipitationCategoryThen == 0:
		htmlout += """uppehåll"""
	if precipitationCategoryThen == 1:
		htmlout += """snö"""
	if precipitationCategoryThen == 2:
		htmlout += """snöblandat"""
	if precipitationCategoryThen == 3:
		htmlout += """regn"""
	if precipitationCategoryThen == 4:
		htmlout += """duggregn"""
	if precipitationCategoryThen == 5:
		htmlout += """hagel"""
	if precipitationCategoryThen == 6:
		htmlout += """hagel"""
	htmlout += 	""" och """ + str(round(float(tempThen),0)).rstrip('0').rstrip('.') + """° varmt.</span>
				</div>
				<div id='box'>
					<!---
					<span id="big">""" + str(round(float(nibeExhaustTemp),0)).rstrip('0').rstrip('.') + """°<br/></span>
					<span id="small">...avluftstemp. Elpatron """
	if float(nibeHeaterPower) == 0:
		htmlout += """avstängd."""
	else:	
		htmlout += """igång, """ + str(round(float(nibeHeaterPower),0)).rstrip('0').rstrip('.') + """kW."""
	htmlout += """		
					---->
				</div>
			</div>
		</body>
		<script type="text/javascript">
			
				
		
		</script>
	</html>
	"""

	with open('/var/www/html/brief.html', 'w') as file:
		file.write(htmlout)
		
	print str(datetime.now()) + ": Sleeping..."
	time.sleep(300) 
	
