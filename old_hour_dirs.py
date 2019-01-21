#!/usr/bin/env python3

# assume directories are named
# YYYYMMDDHH
#
# after the UTC date when the first product within it is received.
#  

import shutil, datetime, os, sys

try:
    how_many_hours=int(sys.argv[1])
except:
    print("First argument should be an integer number of hours to retain")
    exit(1)

try:
    os.chdir(sys.argv[2])
except:
    print("Second argument should directory I can visit")
    exit(2)

# 20190120 21:07:09.839819
cutoff=("%s" % ( datetime.datetime.utcnow() -datetime.timedelta(hours=how_many_hours) )).replace('-','').split()
hour=cutoff[1].split(':')[0]

last=cutoff[0]+hour

print( "last is: %s\n" % last )
old_dirs = [] 

for d in os.listdir('.'):
   if d < last : 
       old_dirs.append(d)
       continue
   print( "skipping: %s" % d )

old_dirs.sort()

for d in old_dirs:
   print( "shutil.rmtree(%s)\n" %d )
   shutil.rmtree(d)



