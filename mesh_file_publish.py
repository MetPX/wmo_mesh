#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import os,json,sys,time,argparse,platform
from hashlib import md5

host=platform.node()

parser = argparse.ArgumentParser(description='post some files')

parser.add_argument('--post_broker', default=host )
parser.add_argument('--post_user_name', default='upload')
parser.add_argument('--post_user_password', default='upload')
parser.add_argument('--post_baseurl', default='http://' + host + ':8000/data')
parser.add_argument('--post_base_dir', default= os.getcwd() + '/data')
parser.add_argument('file', nargs='+', type=argparse.FileType('w'), help='files to post')

args = parser.parse_args( )
print( 'args:', args )

client = mqtt.Client()

client.username_pw_set( args.post_user_name, args.post_user_password )
client.connect( args.post_broker )


exchange='xpublic'
topic_prefix='/v03/post'

client.loop_start()

for f in args.file:
    os.stat( f.name )
    
    f = open(f.name,'rb')
    d = f.read()
    f.close()
     
    hash = md5()
    hash.update(d)
    
    now=time.time()
    nsec = ('%.9g' % (now%1))[1:]
    datestamp  = time.strftime("%Y%m%d%H%M%S",time.gmtime(now)) + nsec
      
    relpath = os.path.abspath(f.name).replace( args.post_base_dir, '' )
    if relpath[0] == '/':
        relpath= relpath[1:]
    
    p = json.dumps( (datestamp, args.post_baseurl, relpath, { "sum":"d,"+hash.hexdigest() } )) 
    
    if os.path.dirname(relpath) == '/':
        subtopic=''
    else:
        subtopic=os.path.dirname(relpath)

    t = exchange + topic_prefix + subtopic
    
    print( "topic=%s , payload=%s" % ( t, p ) )
    client.publish(t, p, qos=2 )
    

client.loop_stop()
client.disconnect()
