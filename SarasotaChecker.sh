#!/bin/bash

datstr="$(date +%Y%m%d%H%M%S)"

spidir="$(dirname "$0")/Spiders"
spiscr="$spidir/SiestaRoyale.py"
spiout="$spidir/SiestaRoyale.$datstr.json"
spilog="$spidir/SiestaRoyale.$datstr.log"
arcdir="$spidir/Archive"
arcout=$(ls "$spidir"/SiestaRoyale.*.json 2> /dev/null)
arclog=$(ls "$spidir"/SiestaRoyale.*.log  2> /dev/null)

success=1
echo -n "Archiving files ... "
mkdir -p "$arcdir"
IFS=$'\n'
for file in $arcout
do
	mv "$file" "$arcdir" 2>&1 > /dev/null
	if (( $? )); then success=0; fi
done
for file in $arclog
do
	mv "$file" "$arcdir" 2>&1 > /dev/null
	if (( $? )); then success=0; fi
done
unset IFS
if (( success )); then echo "done!"; else echo "FAIL!"; fi

echo -n "Running spider  ... "
scrapy runspider "$spiscr" -o "$spiout" --logfile "$spilog"
numsuc=$(grep "downloader/response_status_count/200" "$spilog" | awk '{print $2}' | cut -f1 -d,)
numtot=$(grep "downloader/request_count"             "$spilog" | awk '{print $2}' | cut -f1 -d,)
if [ "$numsuc" == "$numtot" ]; then echo "done!"; else echo "FAIL!"; fi
