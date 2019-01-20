#!/usr/bin/env python3
#  mesh_peer - subscribe to a peer and publish locally what you download

import paho.mqtt.client as mqtt
import os, os.path, urllib.request, json, sys, xattr, datetime, calendar, platform

from hashlib import md5
from hashlib import sha512

import argparse

# name of the extended attribute to cache checksums in when calculated
sxa = 'user.sr_sum'
host = platform.node()

parser=argparse.ArgumentParser(description='Subscribe to one peer, and post what is downloaded')

parser.add_argument('--broker', default='mqtt://' + host, help='mqtt://user:pw@host of peer to subscribe to')
parser.add_argument('--clientid', default=host, help='like an AMQP queue name, identifies a group of subscribers')

# the web server address for the source of the locally published tree.
parser.add_argument('--post_broker', default='mqtt://' + host, help='broker to post downloaded files to')
parser.add_argument('--post_baseurl', default='http://' + host + ':8000/data', help='base url of the files announced')
parser.add_argument('--dir_prefix', default='data', help='local sub-directory to put data in')
parser.add_argument('--post_exchange', default='xpublic', help='root of the topic tree to announce')
parser.add_argument('--post_topic_prefix', default='/v03/post', help='allows simultaneous use of multiple versions and types of messages')

args = parser.parse_args()

def timestr2flt( s ):
    """
       convert a date string to a python epochal time.
    """

    t=datetime.datetime(  int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]), int(s[12:14]), 0, datetime.timezone.utc )
    f=calendar.timegm(  t.timetuple())+float('0'+s[14:])
    return(f)


def sum_file( filename, algo ):
    """
      calculate the checksum of a file using the given algorithm. return a sum header.
      side effect: stores the checksum in a file attribute, if the sum is already available there, then use it.
    """
    global sxa


    a = xattr.xattr( filename )
    if sxa in a.keys():
        print( "retrieving sum" )
        return a[sxa].decode('utf-8')
 
    print( "calculating sum" )
    if algo in [ 'd', 's' ]:
        f = open(filename,'rb')
        d = f.read()
        f.close()
    elif algo in [ 'n' ]:
        d=filename
 
    if algo in [ 'd', 'n']:
        hash = md5()
    elif algo is 's':
        hash = sha512()

    hash.update(d) 
    sf = algo + ',' + hash.hexdigest()
    xattr.setxattr(filename, sxa, bytes(sf,'utf-8') )
    return sf
    


def mesh_download( m, doit=False ):
    """
       If it isn't already here, download the file announced by the message m.
       If you download it, then publish to  the local broker.
    """

    global post_client

    # from sr_postv3.7.rst:   [ m[0]=<datestamp> m[1]=<baseurl> m[2]=<relpath> m[3]=<headers> ]
    d= args.dir_prefix + '/' + os.path.dirname(m[2])

    url = m[1] + '/' + m[2]

    fname=os.path.basename(m[2])

    if not os.path.isdir(d) and doit:
        os.makedirs(d)
        pass
    
    p =  d + '/' + fname 

    FirstTime=True
    if os.path.exists( p ):
        FirstTime=False
        print( "file exists: %s. Should we download? " % p )

        if 'sum' in m[3].keys():

            sumstr = sum_file(p, m[3]['sum'][0] )
            print( "hash: %s" % sumstr )
            if sumstr == m[3]['sum']:
               print( "same content: ", p )
               return

    print( "writing: ", p )
    if doit:
       urllib.request.urlretrieve( url, p )    
     
    if FirstTime:
       if 'sum' in m[3].keys():
           xattr.setxattr(p, sxa, bytes(m[3]['sum'],'utf-8') )
       else:
           sum_file(p, m[3]['sum'][0] )

    # after download, publish for others.
    t=args.post_exchange + args.post_topic_prefix + os.path.dirname(m[2])
    body = json.dumps( ( m[0], args.post_baseurl, m[2], m[3]) )

    print( "posting: t=%s, p=%s" % ( t, body ) ) 
    post_client.publish( topic=t, payload=body, qos=2 )


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe( '#' )

id=0

def on_message(client, userdata, msg):
    global id
    id = id + 1
    m = json.loads(msg.payload.decode('utf-8'))
    print( "     id: ", id )
    print( "  topic: ", msg.topic )
    print( "payload: ", m )

    mesh_download(m,True)
    print( " ")


client = mqtt.Client( clean_session=False, client_id=args.clientid )
client.on_connect = on_connect
client.on_message = on_message

# subscribing to a peer.
print('subscribing to # on %s as client: %s' % ( args.broker, args.clientid ))
sub = urllib.parse.urlparse(args.broker)
if sub.username != None: 
    client.username_pw_set( sub.username, sub.password )
client.connect( sub.hostname )


# get ready to pub.
post_client = mqtt.Client()
pub = urllib.parse.urlparse(args.post_broker)
if sub.username != None: 
    post_client.username_pw_set( pub.username, pub.password )
post_client.connect( pub.hostname )
print('ready to post to %s as %s' % ( pub.hostname, pub.username ))

client.loop_forever()

