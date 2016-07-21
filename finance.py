#!/usr/bin/env python

import web, re, datetime, itertools, time, csv, math, sendmail
from students import get_student_list

root = "/finance"
host = "apps.olin.edu"
finance_email = "Carol Kelley <Carol.Kelley@olin.edu>"

web.config.debug = True

db = web.database(dbn='sqlite', db='finance.sqlite3')

urls = (
  '/', 'index',
  '/groups/?', 'groups',
  '/groups/(\d+)/?', 'group',
  '/groups/(\d+)/(\d+)/?', 'expense',
  '/reimbursements/?', 'reimbursements',
  '/reimbursements/notify', 'reimbursements_notify',
  '/reimbursements/mark', 'reimbursements_mark',
  '/transactions/?', 'transactions',
  '/transactions/mark', 'transactions_mark',
  '/backup/?', 'backup',
  '/students/?', 'students'
)

def currency_float(amount):
	amount = (amount or 0) / 100.0
	temp = "%.2f" % abs(amount)
	profile = re.compile(r"(\d)(\d\d\d[.,])")
	while 1:
		temp, count = re.subn(profile,r"\1,\2",temp)
		if not count: break
	return temp

def currency(amount, parens = True):
	temp = currency_float(amount)
	return ("(%s)" if amount < 0 and parens else "%s") % ("$" + temp)

def currency_value(amount):
	amount = (amount or 0)
	return '<span class="%s">%s</span>' % ("neg" if amount < 0 else "pos" if amount > 0 else "", currency(amount))

def type_sign(type):
	if type == "p-card" or type == "reimbursement":
		return -1
	return 1

def parse_currency(val):
	return round(float(re.compile(r'[^\d.]+').sub('', val))*100)

def get_club_by_expense(expense):
	clubs = list(db.select('club', {"budget": expense.budget}, where='sao_budget=$budget')) + \
		list(db.select('club', {"budget": expense.budget}, where='revenue_budget=$budget'))
	return clubs[0]	

def student_email(id):
	return id + "@students.olin.edu"

#########
# users
#########

import base64, re
from M2Crypto import RSA

def verify_username(enc, username):
	return True
	try:
		pub_key = RSA.load_pub_key("/var/www/apps/auth/pub/%s.pem" % username)
		ctxt = base64.b64decode(enc)
		ptxt = pub_key.public_decrypt(ctxt, 1)
		pat = re.compile(r'(?P<length>[0-9]+)#(?P<name>.*)')
		nlen, name = pat.match(ptxt).groups()
		if len(name) != int(nlen):
			return None
		return name == username
	except:
		return None

user = None

def get_olinauth_user():
	global user
	
	# cache
	if user:
		return user
		
	key = web.cookies().get('olin-auth-key')
	username = web.cookies().get('olin-auth-username')
	if key and username and verify_username(key, username):
		user = username
	else:
		user = False
	return user

def is_admin():
	return get_olinauth_user() in ["tryan", "cmarra"]

###############
# web.py setup
###############

render = web.template.render('templates', base='base', globals={
	"re": re,
	"time": time,
	"datetime": datetime,
	"itertools": itertools,
	"sum": sum,

	"root": root,
	"db": db,
	"currency_float": currency_float,
	"currency": currency,
	"currency_value": currency_value,
	"get_club_by_expense": get_club_by_expense,
	"get_olinauth_user": get_olinauth_user,
	"is_admin": is_admin
	})

#########
# routes
#########

#
# /
#

class index:

	# main page

	def GET(self):
		return render.index()

#
# /groups/
#

class groups:

	# view club list

	def GET(self):
		return render.groups()

	# add new club

	def POST(self):
		if not is_admin():
			return web.seeother('/')
		
		# begin sql transaction
		t = db.transaction()
		try:
			# enter new clubs
			data = web.input(name=[], sao_budget=[], revenue_budget=[], type=[])
			for i in range(len(data.name)):
				if not data.name[i]:
					continue

				sao_budget = db.insert('budget', type='sao')
				db.insert('expense',
					budget = sao_budget,
					date = time.time(),
					description = "Initial",
					type = "allotment",
					completed = True,
					amount = parse_currency(data.sao_budget[i]))

				revenue_budget = db.insert('budget', type='revenue')
				db.insert('expense',
					budget = revenue_budget,
					date = time.time(),
					description = "Initial",
					type = "allotment",
					completed = True,
					amount = parse_currency(data.revenue_budget[i]))

				db.insert('club',
					name = data.name[i],
					sao_budget = sao_budget,
					revenue_budget = revenue_budget,
					type = data.type[i] if data.type[i] in ["class", "club", "organization"] else "club")
		except:
			t.rollback()
			raise
		else:
			t.commit()
		return web.seeother('/groups/')

#
# /groups/(\d+)
#

class group:

	# display club financials

	def GET(self, id):
		i = web.input(edit = None)
		club = db.select('club', {"id": int(id)}, where="id=$id")[0]
		budget_expenses = list(db.select('expense', {"budget": club.sao_budget}, where="budget=$budget", order="date ASC"))
		revenue_expenses = list(db.select('expense', {"budget": club.revenue_budget}, where="budget=$budget", order="date ASC"))
		students = list(db.select('student', order='name ASC'))
		return render.group(club, budget_expenses, revenue_expenses, students, int(i.edit) if i.edit else None)

	# submit club expense

	def POST(self, id):
		if not is_admin():
			return web.seeother('/')
			
		club = db.select('club', {"id": int(id)}, where="id=$id")[0]
		i = web.input()
		print i
		fields = {
			"budget": club.revenue_budget if i.budget == "revenue" else club.sao_budget,
			"date": time.mktime(time.strptime(i.date, "%Y/%m/%d")),
			"description": i.description,
			"type": i.type,
			"completed": int("completed" in i),
			"amount": parse_currency(i.amount)*type_sign(i.type),
			"notes": i.notes,
			"student": i.student if i.type == 'reimbursement' else None
		}
		
		# update or insert
		if 'id' in i:
			db.update('expense', "id=$id", {"id": i.id}, **fields)
		else:
			db.insert('expense', **fields)
		return web.seeother(web.ctx.fullpath)

#
# /groups/(\d+)/(\d+)
#

class expense:

	# delete an expense

	def POST(self, club_id, id):
		if not is_admin():
			return web.seeother('/')
			
		db.delete('expense', vars={"id": int(id)}, where="id=$id")
		return web.seeother('/groups/' + club_id)

#
# /transactions/
#

class transactions:

	# transactions interface

	def GET(self):
		clubs = db.select('club', order='name ASC')
		return render.transactions(web.ctx.query, clubs)

	# enter transactions through interface

	def POST(self):
		if not is_admin():
			return web.seeother('/')
			
		data = web.input(date=[], club=[], budget=[], description=[], amount=[])
		for i in range(len(data.club)):
			if int(data.club[i]) != -1:
				# add reimbursement
				club = db.select('club', {"id": int(data.club[i])}, where="id=$id")[0]
				db.insert('expense',
					budget = club.revenue_budget if data.budget[i] == "revenue" else club.sao_budget,
					date = time.mktime(time.strptime(data.date[i], "%Y/%m/%d")),
					description = data.description[i],
					type = "p-card",
					completed = False,
					amount = -parse_currency(data.amount[i]),
					student = None
					)
		return web.seeother('/transactions')

#
# /transactions/mark
#

class transactions_mark:

	# mark transactions as completed

	def POST(self):
		if not is_admin():
			return web.seeother('/')
			
		db.update('expense', where="type='p-card' AND completed=0", completed=1)
		return web.seeother('/transactions?marked')

#
# /reimbursements/
#

class reimbursements:

	# reimbursements interface

	def GET(self):
		clubs = db.select('club', order='name ASC')
		students = db.select('student', order='name ASC')
		return render.reimbursements(web.ctx.query, clubs, students)

	# enter reimbursements through interface

	def POST(self):
		if not is_admin():
			return web.seeother('/')
			
		data = web.input(date=[], student=[], club=[], budget=[], description=[], amount=[])
		for i in range(len(data.student)):
			if data.student[i] and int(data.club[i]) != -1:
				# add reimbursement
				club = db.select('club', {"id": int(data.club[i])}, where="id=$id")[0]
				student = db.select('student', {"id": data.student[i]}, where='id=$id')[0]
				db.insert('expense',
					budget = club.revenue_budget if data.budget[i] == "revenue" else club.sao_budget,
					date = time.mktime(time.strptime(data.date[i], "%Y/%m/%d")),
					description = data.description[i],
					type = "reimbursement",
					completed = False,
					amount = -parse_currency(data.amount[i]),
					student = student.id
					)
		return web.seeother('/reimbursements')

#
# /reimbursements/notify
#

class reimbursements_notify:

	# route to send out financial emails

	def POST(self):
		web.header('Content-type','text/html')

		yield """<!DOCTYPE html>
<html><head><title>Reimbursement Mailer</title></head>
<body onload="window.scrollTo(0, document.body.scrollHeight)">Loading..."""

		expenses = list(db.select('expense', where="type='reimbursement' AND completed=0"))

		# finance office emails
		table = """<table border="1" style="border-collapse: collapse">
<tr><th>Date</th><th>Student</th><th>Email</th><th>Group(s)</th><th>Amount</th><th>Petty Cash</th></thead>"""
		keyfunc = lambda x : x.student
		for student_id, student_expenses in itertools.groupby(sorted(expenses, key=keyfunc), keyfunc):
			student = db.select('student', {"id": student_id}, where="id=$id")[0]
			clubs = []
			total = 0
			for expense in student_expenses:
				club = get_club_by_expense(expense)
				clubs.append(club.name)
				total += expense.amount

			table += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
				time.strftime("%Y/%m/%d", time.localtime(expense.date)),
				student.name,
				student_email(student.id),
				"/".join(set(clubs)),
				currency(total, parens = False),
				"Yes" if abs(total) <= 2500 else "No")
		table += "</table>"
		msg="""
<p>The following student reimbursements are being submitted:</p>

%s

<p>Reply to this email if you have any followup questions.</p>

<p>Thanks!<br>
SAO Finance</p>
""" % (table,)
		try:
			# send financial services mails
			sendmail.send_mail(sender="SAO Mailer <sao@olin.edu>",
				to=[finance_email],
				cc=["timothy.ryan@students.olin.edu", "SAO Mailer <sao@olin.edu>"],
				subject="Reimbursements Report " + time.strftime("%m/%d/%Y"),
				body=msg,
				html = True)
		except Exception, e:
			yield "<h1>ERROR IN SENDING MAIL: " + str(e) + "</h1>"
			raise e

		yield "<h1>Financial Summary</h1><blockquote>%s</blockquote><hr>" % msg

		# student emails
		yield "<h1>Student Emails</h1><ul>"
		keyfunc = lambda x : x.student
		for student_id, student_expenses in itertools.groupby(sorted(expenses, key=keyfunc), keyfunc):
			student = db.select('student', {"id": student_id}, where="id=$id")[0]

			table = """<table border="1" style="border-collapse: collapse">
<tr><th>Date</th><th>Group</th><th>Description</th><th>Amount</th></thead>"""
			for expense in student_expenses:
				club = get_club_by_expense(expense)
				table += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (time.strftime("%Y/%m/%d", time.localtime(expense.date)), club.name, expense.description, currency(expense.amount, parens = False))
			table += "</table>"

			# author email
			msg="""
<p>%s,</p>

<p>The following reimbursements for you have been submitted:</p>

%s

<p>Please wait at least two weeks for this reimbursement to show up in your account or mailbox, or set up direct deposit through financial services if it hasn't been configured yet.</p>

<p>Thanks!<br>
SAO Finance</p>
""" % (student.name, table)#(host, student.id))
			#"""<p>Go to <a href="%s">%s</a> for more information on your reimbursements. Reply to this email if you have any questions.</p>"""

			# send student email
			sendmail.send_mail(sender="SAO Mailer <sao@olin.edu>",
				to=["%s <%s>" % (student.name, student_email(student.id))],
				cc=["timothy.ryan@students.olin.edu", "SAO Mailer <sao@olin.edu>"],
				subject="Your reimbursements have been submitted!",
				body=msg,
				html = True)
			# add to output
			yield "<li><h2>Email to %s</h2><blockquote>%s</blockquote></li>" % (student_email(student.id), msg)
		yield "</ul><hr>"

		yield "<p id='end'><strong style='color: green'>Done.</strong> <a href='" + root + "/reimbursements/'>Click here</a> to continue.</p></body></html>"
		yield "\r\n"

#
# /reimbursements/mark
#

class reimbursements_mark:

	# mark reimbursements as completed

	def POST(self):
		if not is_admin():
			return web.seeother('/')
			
		db.update('expense', where="type='reimbursement' AND completed=0", completed=1)
		return web.seeother('/reimbursements?marked')

#
# /students/
#

class students:
	
	# student list

	def GET(self):
		return render.students(db.select('student', order='name ASC'))

	# update student list from server
	# use 'yield' to give live updates for 

	def POST(self):
		if is_admin():
			i = web.input()
			students = get_student_list("MILKYWAY\\" + i.username, i.password)

			web.header('Content-type','text/html')

			if students:
				# begin sql transaction
				t = db.transaction()
				try:
					db.query("DELETE FROM student")

					yield '<html><body><h1>Updating Students</h1>'
					for name, email in students.iteritems():
						yield 'Added student ' + name + '...<br>'
						db.insert('student', id=re.sub(r'@.*$', '', email), name=name)
				except:
					t.rollback()
					raise
				else:
					t.commit()

				yield "<p>Done.</p><script>window.location.href = '" + root + "/students/';</script></body></html>"
			else:
				yield "<p style='color: red;'><b>ERROR: No results. Invalid username/password?</b></p></body></html>"

#
# /backup.csv
#

class backup:

	# generate the backup.csv file

	def GET(self):
		web.header('Content-Type', 'application/x-sqlite3')
		web.header('Transfer-Encoding','chunked')    
		web.header("Content-Disposition", "attachment; filename=sao-finances-" + str(int(time.time())) + ".sqlite3")
		return open('finance.sqlite3', 'rb').read()

app = web.application(urls, globals())
if __name__ == "__main__":
	app.run()
