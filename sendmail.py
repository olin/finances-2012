import smtplib
from email.mime.text import MIMEText

def send_mail(**kargs):
	server = "localhost"

	# Prepare actual message

	sender = kargs['sender']
	to = kargs['to']
#	to = ["timothy.ryan@students.olin.edu"]
	cc = kargs.get('cc', [])
#	cc = []
	subject = kargs['subject']
	html = kargs.get('html', False)
	body = kargs['body']

	# prepare message
	msg = MIMEText(body, 'html' if html else 'plain')
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = ", ".join(to)
	if cc:
		msg['CC'] = ", ".join(cc)

	# send mail
	server = smtplib.SMTP(server)
	server.sendmail(sender, to + cc, msg.as_string())
	server.quit()
