import os, sys, requests, datetime, filecmp, smtplib
from html.parser import HTMLParser
from email.mime.text import MIMEText
from urllib.request import urlopen
from bs4 import BeautifulSoup

fetchPage = True
htmlfile = "SarasotaCalendar.html"
statfile = "SarasotaVacancies.txt"
webpage = None

month = str(7)
if datetime.date(datetime.date.today().year, 7, 4) > datetime.date.today():
	year = str(datetime.datetime.today().year)
else:
	year = str(datetime.datetime.today().year + 1)

url  = "http://rentals.siestaroyale.com/rns/search/Availability-Calendar.aspx"
#url  = "https://www.siestaroyale.com/vacation-rentals/rentals-availability-calendar/"
post = {}

if not fetchPage:
	print("Opening cached webpage")
	if os.path.isfile(htmlfile):
		print("File from %d minutes ago found" % round((datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(htmlfile))).seconds/60, 0))
		with open(htmlfile, "r") as fh:
			webpage = fh.read()
	else:
		print("Cached file not found")
		fetchPage = True

if fetchPage:
	print("Fetching webpage")
	with urlopen(url) as fh:
		soup = BeautifulSoup(fh.read(), "html.parser")
	for var in soup.find_all("input"):
		post[var['name']] = var['value']
	for var in soup.find_all("select"):
		if "month" in var['name'].lower():
			post[var['name']] = month
		elif "year" in var['name'].lower():
			post[var['name']] = year
		else:
			post[var['name']] = var['value']
	print("Submitting request")
	resp = requests.post(url, data=post)
	webpage = resp.content.decode("utf-8")
	with open(htmlfile, "w+") as fh:
		fh.write(webpage)

if webpage is None: exit(1)

struct = [{'type': 'Header', 'data': [], 'avail': []}]

soup = BeautifulSoup(webpage, "html.parser")
table = soup.find(id="availCal")
rows = table.find_all("tr")
for row in rows:
	if row.th is not None:
		unit_type = row.th.text
		struct.append({'type': unit_type, 'data': [], 'avail': []})
	else: struct[-1]['data'].append(row)

for var in soup.find_all("select"):
	if "month" in var['name'].lower():
		for opt in var.find_all("option"):
			if 'selected' in opt.attrs:
				month = opt.text
	elif "year" in var['name'].lower():
		for opt in var.find_all("option"):
			if 'selected' in opt.attrs:
				year = opt.text

def pad_title(string, length):
	if string is not None:
		hlen = len(string) + 2
		plen = int((length - hlen)/2)
	else: plen = length
	for i in range(plen): sys.stdout.write("#")
	if string is not None:
		sys.stdout.write(" %s " % string)
		for i in range(length-plen-hlen): sys.stdout.write("#")
	print()

pad_title("Availability Calendar for %s %s" % (month, year), 104)
for d in struct:
	if d['type'] == "Header": continue
	else:
		pad_title(d['type'], 104)
		for row in d['data']:
			items = row.find_all("td")
			unit = None
			for i, v in enumerate(items):
				if i == 0:
					unit = v.a.text.split(" - ")[1]
					sys.stdout.write("Unit %-6s" % (unit + ":"))
				else:
					if not "linked-day" in v.attrs['class']:
						sys.stdout.write(" %02d" % int(v.text))
						if int(v.text) == 4: d['avail'].append(unit)
					else:
						sys.stdout.write("   ")
			print()

with open(statfile+".new", "w+") as fh:
	string = "Fourth of July Vacancies for %s" % year
	pad_title(string, 104)
	fh.write(string+"\n")
	for d in struct:
		if d['type'] == "Header": continue
		string = "%-22s" % (d['type'] + ":")
		sys.stdout.write(string)
		fh.write(string)
		if len(d['avail']) == 0:
			string = " None"
			sys.stdout.write(string)
			fh.write(string)
		else:
			for unit in d['avail']:
				string = " %s" % unit
				sys.stdout.write(string)
				fh.write(string)
		string = "\n"
		sys.stdout.write(string)
		fh.write(string)
pad_title(None, 104)

try:
	if filecmp.cmp(statfile, statfile+".new"):
		print("Nothing has changed from last time")
	else:
		print("Vacancy state has changed! Sending email")

		# Read authentication information from auth.py:
		# Variables EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_FROM, and EMAIL_TO should be defined.
		with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'auth.py')) as f: exec(f.read())

		with open(statfile+".new") as fh:
			msg = MIMEText('<font face="Courier New, Courier, monospace">' + fh.read().replace(' ', '&nbsp;').replace('\n', '<br />') + '</font>', 'html')
		msg['Subject'] = "Siesta Royale Vacancy Change"
		msg['From'] = EMAIL_FROM
		msg['To'] = ', '.join(EMAIL_TO)

		s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
		s.starttls()
		s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
		s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
		s.quit()

except FileNotFoundError:
	print("No previous state, waiting for next run")

os.rename(statfile+".new", statfile)
