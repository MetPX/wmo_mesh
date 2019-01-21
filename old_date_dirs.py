#!/usr/bin/env python3

import shutil, datetime, os, sys

try:
    how_many_hours=int(sys.argv[1])
except:
    print("First argument should be an integer number of days to retain")
    exit(1)

try:
    os.chdir(sys.argv[2])
except:
    print("Second argument should directory I can visit")
    exit(2)

last=("%s" % ( datetime.date.today() -datetime.timedelta(hours=how_many_hours) )).replace('-','')

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
   #shutil.rmtree(d)



