#!/usr/bin/python
# -*- coding: utf-8 -*-

# Import modules for CGI handling 
import cgi, cgitb 
import requests
import json
from datetime import datetime
from datetime import timedelta

# Create instance of FieldStorage 
form = cgi.FieldStorage() 
command = form.getvalue('command')
	
###
### Getting weather data from SMHI
###

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
#need to fix - why using nibeOutTemp here? 
#windChill = 13.12 + 0.625*float(nibeOutTemp) - 13.956*float(windSpeedNow)**0.16 + 0.48669*float(nibeOutTemp)*float(windSpeedNow)**0.16

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

		
if command == "windDirNow":
	print windDirNow