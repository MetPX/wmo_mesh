#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import os,json,sys,time,argparse,platform,urllib.parse
from hashlib import md5
from base64 import b64decode, b64encode
import mimetypes

host=platform.node()

rcs = [ "Connection successful", "Connection refused – incorrect protocol version", 
        "Connection refused – invalid client identifier", "Connection refused – server unavailable",
        "Connection refused – bad username or passwor", "Connection refused – not authorised", 
        "unknown error" 
      ]

def pub_connect(client, userdata, flags, rc):
    if not (0 <= rc <=5): rc=6
    print( rcs[rc] )

def pub_publish(client, userdata, mid):
    print("published mid=%s" % ( mid ) )

parser = argparse.ArgumentParser(\
     description='post some files', \
     formatter_class=argparse.ArgumentDefaultsHelpFormatter )



parser.add_argument('--encoding', choices=[ 'text', 'binary', 'guess'], \
    help='encode payload in base64 (for binary) or text (utf-8)')
parser.add_argument('--inline', dest='inline', action='store_true', help='include file data in the message')
parser.add_argument('--inline_max', type=int, default=1024, help='maximum message size to inline')
parser.set_defaults( encoding='guess', inline=False )
parser.add_argument('--header', nargs=1, action='append', help='name=value user defined optional metadata' )
parser.add_argument('--post_broker', default='mqtt://' + host, help=" mqtt://user:pw@host - broker to post to" )
parser.add_argument('--post_baseUrl', default='http://' + host + ':8000/data', help='base of the tree to publish')
parser.add_argument('--post_baseDir', default= os.getcwd() + '/data', help='local directory corresponding to baseurl')
parser.add_argument('--post_exchange', default='xpublic', help='root of the topic hierarchy (similar to AMQP exchange)')
parser.add_argument('--post_topicPrefix', default='/v03/post', help='means of separating message versions and types.')
parser.add_argument('file', nargs='+', type=argparse.FileType('r'), help='files to post')

args = parser.parse_args( )

headers={}

if args.header:
    for h in args.header:
        (n,v) = h[0].split('=')
        headers[n] = v


post_client = mqtt.Client( protocol=mqtt.MQTTv311 )

post_client.on_connect = pub_connect
post_client.on_publish = pub_publish

pub = urllib.parse.urlparse( args.post_broker) 
if pub.username != None:
    post_client.username_pw_set( pub.username, pub.password )
post_client.connect( pub.hostname )

post_client.loop_start()

for f in args.file:
    os.stat( f.name )
    
    f = open(f.name,'rb')
    d = f.read()
    f.close()
     
    h = md5()
    h.update(d)
    if args.inline and len(d) < args.inline_max:
          
       if args.encoding == 'guess':
           e = mimetypes.guess_type(f.name)[0]
           binary= not e or not ( 'text' in e )
       else:
           binary =  (args.encoding == 'text')

       if binary:
           headers[ "content" ] = { "encoding": "base64", "value": b64encode(d).decode('utf-8') }  
       else:
           headers[ "content" ] = { "encoding": "utf-8", "value": d.decode('utf-8') }  
    
    now=time.time()
    nsec = ('%.9g' % (now%1))[1:]
    datestamp  = time.strftime("%Y%m%dT%H%M%S",time.gmtime(now)) + nsec
      
    relpath = os.path.abspath(f.name).replace( args.post_baseDir, '' )
    if relpath[0] == '/':
        relpath= relpath[1:]
    
    headers[ "pubTime" ] = datestamp
    headers[ "baseUrl" ] = args.post_baseUrl
    headers[ "relPath" ] = relpath
    headers[ "sum" ] = { "method": "md5", "value": b64encode(h.digest()).decode('utf-8') }
    p = json.dumps( headers ) 
    
    if os.path.dirname(relpath) == '/':
        subtopic=''
    else:
        subtopic=os.path.dirname(relpath)

    t = args.post_exchange + args.post_topicPrefix + '/' + subtopic
    
    print( "topic=%s , payload=%s" % ( t, p ) )
    info = post_client.publish(t, p, qos=1 )
    info.wait_for_publish()
    

post_client.loop_stop()
