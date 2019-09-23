import scrapy
import re
from datetime import datetime

verbose = False

class SiestaRoyaleSpider(scrapy.Spider):
    name = 'SiestaRoyale'
    allowed_domains = ['siestaroyale.com']
    start_urls = ['https://www.siestaroyale.com/vacation-rentals/rentals-availability-calendar/']

    def parse(self, response):
        # Pull in current date and split into year, month, and day
        cy, cm, cd = [int(d) for d in datetime.now().strftime("%Y,%m,%d").split(",")]
        # Define target date to determine whether to pass current or next year
        ty, tm, td = (cy, 7, 4)
        # If current month is greater than target month OR current month is target month,
        # but current day is greater or equal to target day, pass next year
        if cm > tm or cm == tm and cd >= td: ty += 1
        return scrapy.FormRequest.from_response(response, formdata={'monthyear': '%02d/%4d' % (tm, ty)}, callback=self.afterSelect)

    def afterSelect(self, response):

        table = scrapy.Selector(text=''.join([re.sub('\s+', ' ', x) for x in response.css("table.property-availability").getall()]).replace('> ', '>').replace(' <', '<'))

        info = {}

        curr_dates = None
        curr_style = None
        curr_prpty = None
        curr_warns = []

        info['AvailMonths'] = response.css("select#monthyear option::attr(value)").getall()
        info['SelectMonth'] = info['AvailMonths'][[i for i, s in enumerate(response.css("select#monthyear option").getall()) if 'option selected' in s][0]]
        for row in table.css("tr"):
            br = row.css("td.bedrooms")
            if br:
                curr_style = br.css("::text").getall()[0]
                if verbose: print("Style: %s" % curr_style)
                if not curr_style in info:
                    info[curr_style] = {}
            pn = row.css("td.property-name")
            if pn:
                if curr_style is None:
                    print("WARN: Style has not been defined yet!")
                    curr_warns.append("style")
                curr_prpty = pn.css("a::attr(title)").getall()[0]
                if verbose: print("  Property:", curr_prpty)
                if not curr_prpty in info[curr_style]:
                    info[curr_style][curr_prpty] = {}
                info[curr_style][curr_prpty]['Address'] = pn.css("a::attr(href)").getall()[0]
                if verbose: print("    Address:", info[curr_style][curr_prpty]['Address'])
            av = row.css("td.date-day")
            if av:
                if curr_style is None:
                    print("WARN: Style has not been defined yet!")
                    curr_warns.append("style")
                if curr_prpty is None:
                    print("WARN: Property has not been defined yet!")
                    curr_warns.append("property")
                status = [s.replace('date-day', '').replace('firstday bothdays', 'bothdays') for s in av.css("::attr(class)").getall()]
                info[curr_style][curr_prpty]['Booked'] = ['booked' in s for s in status]
                info[curr_style][curr_prpty]['FirstDay'] = ['firstday' in s for s in status]
                info[curr_style][curr_prpty]['LastDay'] = ['lastday' in s for s in status]
                info[curr_style][curr_prpty]['BothDays'] = ['bothdays' in s for s in status]
                info[curr_style][curr_prpty]['Weekend'] = ['weekend' in s for s in status]
                if verbose: print("    Status:", info[curr_style][curr_prpty]['Status'])
                info['Dates'] = av.css("::text").getall()
                if verbose: print("    Dates:", info['Dates'])
                if curr_dates is not None and curr_dates != info['Dates']:
                    print("WARN: Not all properties have same dates!")
                    curr_warns.append("dates")
                curr_dates = info['Dates']
        info['Warnings'] = curr_warns
        yield info
