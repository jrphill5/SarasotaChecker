#!/usr/bin/env python3

import os, sys, glob, json, math
from datetime import date, datetime
from deepdiff import DeepDiff
from email.mime.text import MIMEText
import smtplib

# Variables EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
# EMAIL_FROM, and EMAIL_TO should be defined in auth.py script
from auth import *

tarday = 4     # Target day to examine in selected month within the JSON
wrpcol = 7     # Number of units to display on one line before wrapping
enhtml = True  # Enable HTML output or only export plain text

dirnam = os.path.dirname(os.path.realpath(__file__))
outfil = os.path.join(dirnam, "index.html")

spidir = os.path.join(dirnam, "Spiders")
arcdir = os.path.join(spidir, "Archive")

def cleanDict(data):
    cleanData = {}
    for k, v in data.items():
        if isinstance(v, dict):
            v = cleanDict(v)
        if not v in (u'', None, {}):
            cleanData[k] = v
    return cleanData

def calcMaxCols(data):
    maxcol = 0
    for k, v in data.items():
        for k, v in v.items():
            if len(v.items()) > maxcol:
                maxcol = len(v.items())
    maxcol += 1
    return maxcol

def parse(info):
    if info['Warnings']:
        print("  Warn: %s" % info['Warnings'])
        warn = True
    else:
        print("  Warn: None")
        warn = False
    
    month, year = [int(d) for d in info['SelectMonth'].split("/")]
    days = [int(d) for d in info['Dates']]
    idx = [i for i, d in enumerate(days) if d == tarday][0]
    dobj = date(year, month, days[idx])
    print("  Date: %s" % dobj)
    
    data = {}

    # Iterate through all unit styles:
    for sty in list(set(info.keys()) - set(['AvailMonths', 'SelectMonth', 'Dates', 'Warnings'])):
        # Iterate through all individual units:
        for unt in info[sty].keys():
            # Extract unit number and location:
            lst = unt.split(" ")
            num =          lst[0]
            loc = " ".join(lst[1:])
            # Create subdictionaries if not exist:
            if loc not in data.keys():      data[loc]      = {}
            if sty not in data[loc].keys(): data[loc][sty] = {}
            # Only include units that are not booked:
            if not info[sty][unt]['Booked'][idx]:
                # Create subdictionary if not exist:
                if num not in data[loc][sty].keys(): data[loc][sty][num] = {}
                # Include stored URL address with unit:
                data[loc][sty][num]['Address'] = info[sty][unt]['Address']
                # Include booking info, but only for selected day:
                for bky in list(set(info[sty][unt].keys()) - set(['Address'])):
                    data[loc][sty][num][bky] = info[sty][unt][bky][idx]

    # Remove empty subdictionaries:
    data = cleanDict(data)

    return data, dobj, warn

try:
    spiout = sorted(glob.glob(os.path.join(spidir, "SiestaRoyale.*.json")), reverse=True)[0]
    update = datetime.strptime(spiout.split(".")[-2], "%Y%m%d%H%M%S")
except:
    print("No data file! Exiting!")
    exit(1)

try: arcfil = sorted(glob.glob(os.path.join(arcdir, "SiestaRoyale.*.json")), reverse=True)[0]
except: arcfil = None

print("New: %s" % spiout.split("/")[-1])
with open(spiout, "r") as fh:
    infonew = json.load(fh)[-1]
datan, dobjn, warnn = parse(infonew)

maxcol = calcMaxCols(datan)

def parseDiff(string):
    string = string.split("root['")[1].split("']['")
    string[-1] = string[-1].split("']")[0]
    return string

if arcfil is not None:
    print("Old: %s" % arcfil.split("/")[-1])
    with open(arcfil, "r") as fh:
        infoold = json.load(fh)[-1]
    datao, dobjo, warno = parse(infoold)

    if dobjn != dobjo:
        print("ERROR: New file is from different month than old file!")
        arcfil = None

    ddiff = DeepDiff(datao, datan, ignore_order=True)

    ddata = {}
    for key, data in [('dictionary_item_added', datan), ('dictionary_item_removed', datao)]:
        if key in ddiff.keys():
            chng = key.split("_")[-1].capitalize()
            if chng not in ddata.keys(): ddata[chng] = {}
            for item in ddiff[key]:
                item = parseDiff(item)
                if item[0] not in ddata[chng].keys(): ddata[chng][item[0]] = {}
                if len(item) == 1:
                    for k1, v1 in sorted(data[item[0]].items()):
                        if k1 not in ddata[chng][item[0]].keys(): ddata[chng][item[0]][k1] = {}
                        for k2, v2 in sorted(v1.items()):
                            if k2 not in ddata[chng][item[0]][k1].keys(): ddata[chng][item[0]][k1][k2] = {}
                            ddata[chng][item[0]][k1][k2]['Address'] = v2['Address']
                elif len(item) == 2:
                    if item[1] not in ddata[chng][item[0]].keys(): ddata[chng][item[0]][item[1]] = {}
                    for k1, v1 in sorted(data[item[0]][item[1]].items()):
                        if k1 not in ddata[chng][item[0]][item[1]].keys(): ddata[chng][item[0]][item[1]][k1] = {}
                        ddata[chng][item[0]][item[1]][k1]['Address'] = v1['Address']
                elif len(item) == 3:
                    if item[1] not in ddata[chng][item[0]].keys(): ddata[chng][item[0]][item[1]] = {}
                    if item[2] not in ddata[chng][item[0]][item[1]].keys(): ddata[chng][item[0]][item[1]][item[2]] = {}
                    ddata[chng][item[0]][item[1]][item[2]]['Address'] = data[item[0]][item[1]][item[2]]['Address']

if enhtml:
    with open(outfil, "w+") as fh:
        fh.write('<!DOCTYPE html>\n')
        fh.write('<html lang="en">\n')
        fh.write('<head>\n')
        fh.write('  <meta charset="utf-8" />\n')
        fh.write('  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n')
        fh.write('  <title>Siesta Royale Availability</title>\n')
        fh.write('  <style>\n')
        fh.write('    body    { text-align:    center; }\n')
        fh.write('    table   { width:         400px;\n')
        fh.write('              margin:        0.75em auto;\n')
        fh.write('              padding:       0.75em;\n')
        fh.write('              border-radius: 1.25em;\n')
        fh.write('              border:        1px solid #000; }\n')
        fh.write('    th      { padding-top:   0.75em; }\n')
        fh.write('    td      { padding:       0.25em 0em;\n')
        fh.write('              text-align:    center;\n')
        fh.write('              min-width:     35px; }\n')
        fh.write('    .fitw   { width:         1px;\n')
        fh.write('              white-space:   nowrap; }\n')
        fh.write('    .right  { text-align:    right;\n')
        fh.write('              padding-right: 0.25em; }\n')
        fh.write('    .foot   { padding-top:   0.75em;\n')
        fh.write('              text-align:    center;\n')
        fh.write('              font-size:     0.75em;\n')
        fh.write('              font-style:    italic; }\n')
        fh.write('    .nopad  { padding-top:   0em; }\n')
        fh.write('  </style>\n')
        fh.write('</head>\n')
        fh.write('<body>\n')
        fh.write('  <table>\n')
        fh.write('    <tr><th class="nopad">Siesta Royale Checker</th></tr>\n')
        fh.write('    <tr><th class="nopad">%s</th></tr>\n' % dobjn.strftime("%A, %B %-d, %Y"))
        fh.write('    <tr><td class="foot">Updated %s</td></tr>\n' % update)
        fh.write('  </table>\n')
        fh.write('  <table>\n')
        fh.write('    <tr><th colspan=%d class="nopad">Availability</th></tr>\n' % (wrpcol+1))
        for loc in sorted(datan.keys(), reverse=True):
            fh.write('    <tr><th colspan=%d>%s</th></tr>\n' % (wrpcol+1, loc))
            for sty in sorted(datan[loc].keys()):
                fh.write('    <tr>\n')
                fh.write('      <td rowspan=%d class="right fitw">%s:</td>\n' % (math.ceil(len(datan[loc][sty].keys())/wrpcol), sty.replace("rooms", "room")))
                for i, num in enumerate(sorted(datan[loc][sty].keys())):
                    adr = datan[loc][sty][num]['Address']
                    fh.write('      <td><a href="%s">%s</a></td>\n' % (adr, num))
                    if i % wrpcol == wrpcol - 1 and i != len(datan[loc][sty].keys()) - 1:
                        fh.write('    </tr>\n    <tr>\n')
                    if i == len(datan[loc][sty].keys()) - 1:
                        for j in range(wrpcol-i%wrpcol-1):
                            fh.write('      <td>&nbsp;</td>\n')
                fh.write('    </tr>\n')
        fh.write('  </table>\n')
        if arcfil is not None:
            for chng, v1 in sorted(ddata.items()):
                fh.write('  <table>\n')
                fh.write('    <tr><th colspan=%d class="nopad">Recently %s</th></tr>\n' % (wrpcol+1, chng))
                for loc, v2 in sorted(v1.items(), reverse=True):
                    fh.write('    <tr><th colspan=%d>%s</th></tr>\n' % (wrpcol+1, loc))
                    for sty, v3 in sorted(v2.items()):
                        fh.write('    <tr>\n')
                        fh.write('      <td rowspan=%d class="right fitw">%s:</td>\n' % (math.ceil(len(v3.keys())/wrpcol), sty.replace("rooms", "room")))
                        for i, (num, v4) in enumerate(sorted(v3.items())):
                            adr = v4['Address']
                            fh.write('      <td><a href="%s">%s</a></td>\n' % (adr, num))
                            if i % wrpcol == wrpcol - 1 and i != len(v3.keys()) - 1:
                                fh.write('    </tr>\n    <tr>\n')
                            if i == len(v3.keys()) - 1:
                                for j in range(wrpcol-i%wrpcol-1):
                                    fh.write('      <td>&nbsp;</td>\n')
                        fh.write('    </tr>\n')
                fh.write('  </table>\n')
        fh.write('</body>\n')
        fh.write('</html>')

    if arcfil is not None and ddata:
        print("Change detected! Sending email!")
        html = open(outfil)
        msg = MIMEText(html.read(), 'html')
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(EMAIL_TO)
        msg['Subject'] = "Siesta Royale Vacancy Change"

        s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        s.starttls()
        s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        s.quit()

else:
    if datan: print("\nAvailability")
    for loc in sorted(datan.keys(), reverse=True):
        print("  %s" % loc)
        for sty in sorted(datan[loc].keys()):
            print("    %s" % sty.replace("rooms", "room"))
            for num in sorted(datan[loc][sty].keys()):
                sys.stdout.write("      %s: " % num)
                print(datan[loc][sty][num])

    if arcfil is not None:
        if ddata: print("\nChanges")
        for k1, v1 in ddata.items():
            print("  %s" % k1)
            for k2, v2 in v1.items():
                print("    %s" % k2)
                for k3, v3 in v2.items():
                    print("      %s" % k3)
                    for k4, v4 in v3.items():
                        print("        Unit: %s" % k4)
                        for k5, v5 in v4.items():
                            print("        %s: %s" % (k5, v5))
