import urllib2, re, getpass, json, urllib2
from urllib2 import URLError
from ntlm import HTTPNtlmAuthHandler

SAO_URL = "http://olinfinance.appspot.com/students/"

#####################
# EXCHANGE CONNECTOR
#####################
# This script simply sends a request using the ExpandDL
# SOAP interface for Outlook 2007. If Olin winds up updating
# their Exchange server, (it figures, also,) update to the
# newest SOAP connector.

def get_student_list(user, password):
	url = "https://webmail.olin.edu/ews/exchange.asmx"

	# setup HTTP password handler
	passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
	passman.add_password(None, url, user, password)
	# create NTLM authentication handler
	auth_NTLM = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(passman)
	proxy_handler =  urllib2.ProxyHandler({})
	opener = urllib2.build_opener(proxy_handler,auth_NTLM)

	# this function sends the custom SOAP command which expands
	# a given distribution list
	def expand_dl(email):
		data = """<?xml version="1.0" encoding="utf-8"?>
	<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
		           xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
	  <soap:Body>
		<ExpandDL xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
		          xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
		    <Mailbox>
		      <t:EmailAddress>%s</t:EmailAddress>
		    </Mailbox>
		</ExpandDL>
	  </soap:Body>
	</soap:Envelope>
	""" % email
		# send request
		headers = {'Content-Type': 'text/xml; charset=utf-8'}
		req = urllib2.Request(url, data=data, headers=headers)
		res = opener.open(req).read()
		# parse result
		re_email = re.compile('<t:EmailAddress>([^<]+)</t:EmailAddress>')
		re_name = re.compile('<t:Name>([^<]+)</t:Name>')
		return dict(zip(re_name.findall(res), re_email.findall(res)))

	# first we expand the distribution list "StudentsAll", a list of all current classes (i.e. 2010-2013)
	# after, we expand each of these lists to get student email addresses
	students = {}
	for _, stuclass in expand_dl('StudentsAll').iteritems():
		students.update(expand_dl(stuclass))
	return students

#####################
# COMMAND LINE ENTRY
#####################

print "Update student list on SAO website"
print "* For Python 2.6+"
print "* Custom update_sao_students.py by Tim Cameron Ryan (tim@tim-ryan.com)"
print "* NTLM library at http://code.google.com/p/python-ntlm/"
print ""

username = "MILKYWAY\\" + raw_input("Username ('tryan', no MILKYWAY): ")
password = getpass.getpass()

print "\nDownloading student list..."
students = get_student_list(username, password)
if students:
	try:
		# POST request to website
		print "Uploading to SAO website..."
		response = urllib2.urlopen(SAO_URL, json.dumps(students))
		print response.read()
		print "The website is now updated!"
	except URLError, e:
		print "Upload failed: Status", e.code
		print e.read()
else:
	print "No results returned. Was your password correct?"
