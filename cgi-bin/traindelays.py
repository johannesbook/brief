#!/usr/bin/python
# -*- coding: utf-8 -*-

# Import modules for CGI handling 
import cgi, cgitb 
import urllib2
import xml.etree.ElementTree as ET

# Create instance of FieldStorage 
#form = cgi.FieldStorage() 
#first_name = form.getvalue('first_name')
#last_name  = form.getvalue('last_name')
#print "<h2>Hello hejsan %s %s</h2>" % (first_name, last_name)


	
###
### Checking train delays with skånetrafiken
###

url = 'http://www.labs.skanetrafiken.se/v2.2/resultspage.asp?cmdaction=previous&selPointFr=malm%F6%20C|80000|0&selPointTo=trelleborg|87071|0'
file2 = urllib2.urlopen(url)
data = file2.read()
file2.close()

root = ET.fromstring(data)
delays = 0 

for journey in root.iter('{http://www.etis.fskab.se/v1.0/ETISws}Journey'):
	#print("Trip: "+ journey[1].text + " -> " + journey[2].text)
	depDelay = int(journey[12][0][7][0][2].text)
	arrDelay = int(journey[12][0][7][0][4].text)
	#print "depDel: " + str(depDelay)
	#print "arrDel: " + str(arrDelay)
	if ((depDelay > 5) or (arrDelay > 5)):
		delays = 1

print delays #return result - is any of the last five trains from Malmö to Trelleborg late at departure or arrival? 
