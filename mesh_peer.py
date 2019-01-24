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
parser.add_argument('--verbose', default=1, type=int, help='how chatty to be 0-rather quiet ... 3-quite chatty really')

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
    global sxa,args

    if args.verbose > 1:
        print( "calculating sum" )

    if algo in [ 'd', 's' ]:
        f = open(filename,'rb')
        d = f.read()
        f.close()
    elif algo in [ 'n' ]:
        d=filename
 
    if algo in [ 'd', 'n']:
        h = md5()
    elif algo is 's':
        h = sha512()

    h.update(d) 
    sf = algo + ',' + h.hexdigest()
    xattr.setxattr(filename, sxa, bytes(sf,'utf-8') )
    return sf
    


def mesh_subpub( m, doit=False ):
    """
       If it isn't already here, download the file announced by the message m.
       If you download it, then publish to  the local broker.
    """
    global post_client,args

    # from sr_postv3.7.rst:   [ m[0]=<datestamp> m[1]=<baseurl> m[2]=<relpath> m[3]=<headers> ]
    d= args.dir_prefix + '/' + os.path.dirname(m[2])

    url = m[1] + '/' + m[2]

    fname=os.path.basename(m[2])

    if not os.path.isdir(d) and doit:
        os.makedirs(d)
        pass
    
    p =  d + '/' + fname 

    if os.path.exists( p ):
        if args.verbose > 1:
            print( "file exists: %s. Should we download? " % p )

        a = xattr.xattr( p )
        if sxa in a.keys():
           if args.verbose > 1:
               print( "retrieving sum" )
           sumstr = a[sxa].decode('utf-8')
        else: 
           sumstr = sum_file(p, m[3]['sum'][0] )

        print( "hash: %s" % sumstr )
        if sumstr == m[3]['sum']:
            if args.verbose > 1:
                print( "same content: ", p )
            return
    if args.verbose > 1:
        print( "writing: ", p )

    if doit:
       urllib.request.urlretrieve( url, p )    
       sumstr = sum_file(p, m[3]['sum'][0] )
     
    m[3]['sum'] = sumstr

    # after download, publish for others.
    t=args.post_exchange + args.post_topic_prefix + os.path.dirname(m[2])
    body = json.dumps( ( m[0], args.post_baseurl, m[2], m[3]) )

    info = post_client.publish( topic=t, payload=body, qos=1 )
    info.wait_for_publish()

    if args.verbose > 0:
         print( "published: t=%s, body=%s" % ( t, body ) )


rcs = [ "Connection successful", "Connection refused – incorrect protocol version",
        "Connection refused – invalid client identifier", "Connection refused – server unavailable",
        "Connection refused – bad username or passwor", "Connection refused – not authorised",
        "unknown error"
      ]

def pub_connect(client, userdata, flags, rc):
    if not ( 0 <= rc <= 5) : rc=6
    print( "on publishing:", rcs[rc] )

def sub_connect(client, userdata, flags, rc):
    if rc > 5: rc=6
    print( "on connection to subscribe:", rcs[rc] )
    client.subscribe( args.post_exchange + args.post_topic_prefix + '/#' )

def pub_connect(client, userdata, flags, rc):
    print("pub connected with result code "+str(rc))

id=0

def sub_message(client, userdata, msg):
    global id
    id = id + 1
    m = json.loads(msg.payload.decode('utf-8'))
    print( "     id: ", id )
    print( "  topic: ", msg.topic )
    print( "payload: ", m )

    mesh_subpub(m,True)
    print( " ")

def pub_log(client, userdata, level, buf):
    print("pub log:"+buf)

def sub_log(client, userdata, level, buf):
    print("sub log:"+buf)

client = mqtt.Client( clean_session=False, client_id=args.clientid, protocol=mqtt.MQTTv311 )
client.on_connect = sub_connect
client.on_message = sub_message

if args.verbose > 2:
   client.on_log = sub_log

# subscribing to a peer.
print('subscribing to  %s/# on %s as client: %s' % ( args.post_exchange + \
    args.post_topic_prefix, args.broker, args.clientid ) )

sub = urllib.parse.urlparse(args.broker)
if sub.username != None: 
    client.username_pw_set( sub.username, sub.password )
client.connect( sub.hostname )


# get ready to pub.
post_client = mqtt.Client(protocol=mqtt.MQTTv311)

if args.verbose > 2:
    post_client.on_connect = pub_connect
    client.on_log = pub_log

post_client.loop_start()

pub = urllib.parse.urlparse(args.post_broker)
if pub.username != None: 
    post_client.username_pw_set( pub.username, pub.password )

post_client.connect( pub.hostname )

print('ready to post to %s as %s' % ( pub.hostname, pub.username ))

client.loop_forever()



