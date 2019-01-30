#!/usr/bin/env python3 

import sys,json,xattr,os.path,argparse

TODOWNLOAD='to_download.pipe'

if not os.path.exists(TODOWNLOAD):
   os.mkfifo(TODOWNLOAD)

tdp=open(TODOWNLOAD,'w')

sxa = 'user.sr_sum'

for line in sys.stdin:
    m = json.loads(line)
    new_sum=m[3]['sum']
    if os.path.exists(m[2]):
       a = xattr.xattr( p )
       if sxa in a.keys():
            old_sum = a[sxa].decode('utf-8')
            if old_sum == new_sum:
                continue

    print( "%s%s" % ( m[1], m[2] ))
    sys.stdout.flush()
    tdp.write(line)
    tdp.flush()

tdp.close()
