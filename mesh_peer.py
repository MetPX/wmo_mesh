#!/usr/bin/env python3
#  mesh_peer - subscribe to a peer and publish locally what you download

import paho.mqtt.client as mqtt
import os, os.path, urllib.request, json, sys, xattr, datetime, calendar, time, platform

from hashlib import md5
from hashlib import sha512
from base64 import b64decode, b64encode
from mimetypes import guess_type
import argparse

import re

# name of the extended attribute to cache checksums in when calculated
sxa = 'user.sr_integrity'
host = platform.node()

parser=argparse.ArgumentParser( \
     description='Subscribe to one peer, and post what is downloaded' ,\
     formatter_class=argparse.ArgumentDefaultsHelpFormatter )

parser.add_argument('--broker', default='mqtt://' + host, help='mqtt://user:pw@host of peer to subscribe to')
parser.add_argument('--clean_session', type=bool, default=False, help='start a new session, or resume old one?')
parser.add_argument('--clientid', default=host, help='like an AMQP queue name, identifies a group of subscribers')
parser.add_argument('--dir_prefix', default='data', help='local sub-directory to put data in')
parser.add_argument('--encoding', choices=[ 'text', 'binary', 'guess'], help='encode payload in base64 (for binary) or text (utf-8)')

parser.add_argument('--inline', dest='inline', action='store_true', help='include file data in the message')
parser.add_argument('--inline_max', type=int, default=1024, help='maximum message size to inline')

parser.set_defaults( encoding='guess', inline=False )

parser.add_argument('--lag_warn', default=120, type=int, help='in seconds, warn if messages older than that')
parser.add_argument('--lag_drop', default=7200, type=int, help='in seconds, drop messages older than that')

# the web server address for the source of the locally published tree.
parser.add_argument('--post_broker', default='mqtt://' + host, help='broker to post downloaded files to')
parser.add_argument('--post_baseUrl', default='http://' + host + ':8000/data', help='base url of the files announced')
parser.add_argument('--post_exchange', default='xpublic', help='root of the topic tree to announce')
parser.add_argument('--post_topic_prefix', default='/v03/post', help='allows simultaneous use of multiple versions and types of messages')
parser.add_argument('--select', nargs=1, action='append', help='client-side filtering: accept/reject <regexp>' )
parser.add_argument('--subtopic', nargs=1, action='append', help='server-side filtering: MQTT subtopic, wilcards # to match rest, + to match one topic' )
parser.add_argument('--verbose', default=1, type=int, help='how chatty to be 0-rather quiet ... 3-quite chatty really')

args = parser.parse_args()

if args.verbose > 3:
    print( "args: %s" % args )

if args.post_broker.lower() == 'none' :
     args.post_broker=None

if args.subtopic==None:
   args.subtopic=[ '#' ]
else:
   args.subtopic=sum(args.subtopic,[])

if args.verbose > 3:
    print( "subtopics: %s" % args.subtopic )

masks = []

if args.select:
    for s in args.select :
        sel = s[0].split()
        if sel[0] in [ 'accept', 'reject' ]:
            r = re.compile(sel[1])
            m = ( sel[0], r )
        else:
            m = ( sel[0] )
        masks.append(m)

if args.verbose > 2:
    print( "masks: %s" % masks )


def URLSelected( u ):
    """
      implement client side selection.
      apply accept/reject patterns, return True if selected, false if rejected.
      no match? return true.
    """
    global masks
    for m in masks:
        if m[0] in [ 'accept', 'reject' ]:
           if m[1].match(u):
              return ( m[0] == 'accept' )
    return True

def timestr2flt( s ):
    """
       convert a date string to a python epochal time.
    """

    if s[8] == 'T' :
        t=datetime.datetime(  int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[9:11]), int(s[11:13]), int(s[13:15]), 0, datetime.timezone.utc )
        f=calendar.timegm(  t.timetuple())+float('0'+s[15:])
    else:
        t=datetime.datetime(  int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]), int(s[12:14]), 0, datetime.timezone.utc )
        f=calendar.timegm(  t.timetuple())+float('0'+s[14:])
    return(f)

def compute_file_integrity( filename, algo ):
    """
      calculate the checksum of a file using the given algorithm. return a sum header.
      side effect: stores the checksum in a file attribute
    """
    global sxa,args

    if args.verbose > 1:
        print( "calculating sum" )

    if algo in [ 'md5', 'sha512', 'd', 's' ]:
        f = open(filename,'rb')
        d = f.read()
        f.close()
    elif algo in [ 'n' ]:
        d=filename
 
    if algo in [ 'md5', 'md5name', 'd', 'n']:
        h = md5()
    elif algo in [ 'sha512', 's']:
        h = sha512()

    h.update(d) 
    sf = { "method":algo, "value": b64encode(h.digest()).decode('utf-8').strip() }
    xattr.setxattr(filename, sxa, json.dumps(sf).encode('utf-8') )
    return sf
    
def download( url, p, old_sum, new_sum, m ):
    """
       download URL into a local file p, checksum it upon receipt. 
       complain if download failed, perhaps retry.
      
       do 2 attempts, then give up.
    """

    sumstr=None
    attempt=0
    while attempt < 2 :
        if args.verbose > 1:
             print( "writing attempt %s: %s" % (attempt, p) )

        if 'content' in m.keys():
            if args.verbose > 1:
                print( "inline content: ", p )
            # create file if it does not exist, open without truncating for write.
            # this deals with the race condition where two readers compete to write the same file.
            # they will just write the same bytes at the same location, so no harm done... 
            # but must avoid truncation, which is stupidly difficult in python
            f = os.fdopen(os.open(p, os.O_RDWR | os.O_CREAT), 'rb+')
            if m['content']['encoding'] == 'base64':
               f.write( b64decode( m['content']['value'] ) )
            else:
               f.write( m['content']['value'].encode('utf-8' ))
            f.truncate()
            f.close()
            
            
        else:
            if args.verbose > 1:
                print( "download content: ", p )
            try:
                urllib.request.urlretrieve( url, p )    
            except Exception as ex:
                print(ex)

        if os.path.exists( p ):
            # calculate actual checksum, regardless of what the message says.
            sumstr = compute_file_integrity(p, new_sum['method'] )
            if (sumstr[ 'value' ] != new_sum[ 'value' ] ):
                print( "integrity mismatch msg: %s vs. download: %s for %s" % ( sumstr[ 'value' ], new_sum[ 'value' ] ,p ) )
            if (sumstr[ 'value' ] != old_sum[ 'value' ] ): # the 
                attempt=99 
        else:
            attempt = attempt +1

    return sumstr

def mesh_subpub( m ):
    """
       If it isn't already here, download the file announced by the message m.
       If you download it, then publish to  the local broker.
    """
    global post_client,args

    d= args.dir_prefix + '/' + os.path.dirname(m['relPath'])

    url = m['baseUrl'] + '/' + m['relPath']

    if not URLSelected( url ):
       if args.verbose > 1:
           print( "rejected", url )
       return

    fname=os.path.basename(m['relPath'])

    if not os.path.isdir(d): 
        os.makedirs(d)
    
    p =  (d + '/' + fname).replace('//','/') 

    if os.path.exists( p ):
        if args.verbose > 1:
            print( "file exists: %s. Should we download? " % p )

        #retrieve old checksum from file extended attribute.
        a = xattr.xattr( p )
        if sxa in a.keys():
           if args.verbose > 1:
               print( "retrieving sum" )
           old_sum = json.loads(a[sxa])
        else: 
           old_sum = compute_file_integrity(p, m['integrity']['method'] )

        if old_sum == m['integrity']:
            if args.verbose > 1:
                print( "same content: ", p )
            return
    else:
        old_sum = { 'method': 'md5', 'value': '1B2M2Y8AsgTpgAmY7PhCfg==' }  # md5sum for empty file.

    sumstr = download( url, p, old_sum, m['integrity'], m )

    if ( sumstr is None ): 
       print( 'download failed')
       return
 
    m['integrity'] = sumstr

    if args.inline and not 'content' in m.keys():
        s= os.stat(p)
        if args.verbose > 2:
            print( 'inline check sz: %d , max: %d' % (s.st_size, args.inline_max ) )
        if s.st_size < args.inline_max:
            print( 'message is small enough to be inlined. Doing so for local re-publish')
            f = open(p, 'rb') 
            d=f.read()
            f.close()
            if args.encoding == 'guess':
                e = guess_type(p)[0]
                binary= not e or not ( 'text' in e )
            else:
                binary =  (args.encoding == 'text')
     
            if binary:
                m[ "content" ] = { "encoding": "base64", "value": b64encode(d).decode('utf-8').strip() }
            else:
                m[ "content" ] = { "encoding": "utf-8", "value": d.decode('utf-8') }
     
            
    # after download, publish for others.
    t=args.post_exchange + args.post_topic_prefix + os.path.dirname(m['relPath'])
    m[ 'baseUrl' ] = args.post_baseUrl
    body = json.dumps( m )

    if args.post_broker == None:
         return
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
    global args
    if rc > 5: rc=6
    print( "on connection to subscribe:", rcs[rc] )
    for s in args.subtopic:
        subj = args.post_exchange + args.post_topic_prefix + '/' + s
        if args.verbose > 1:
           print( "subtopic:", subj )
        client.subscribe( subj , qos=1 )

def pub_connect(client, userdata, flags, rc):
    print("pub connected with result code "+str(rc))

msg_count=0
total_lag=0

def sub_message(client, userdata, msg):
    """
      callback on receipt of a message. 
      Decode it into a JSON body.
      check lag.
      if not too old, then call subpub.

    """
    global msg_count,total_lag

    m = json.loads(msg.payload.decode('utf-8'))
    print( "  topic: ", msg.topic )
    print( "payload: ", m )

    lag = time.time() - timestr2flt( m['pubTime'] )

    msg_count = msg_count + 1
    total_lag = total_lag + lag

    if lag > args.lag_drop : # picked a number of 2 minutes...
       print( "ERROR: lag is %g seconds, Dropping. " % lag )
       return

    if lag > args.lag_warn : 
       print( "WARNING: lag is %g seconds, risk of message loss from server-side queueing." % lag )
    else:
       print( "    lag: %g   (mean lag of all messages: %g )" % ( lag, total_lag/msg_count ) )

    mesh_subpub(m)
    print( " ")

def pub_log(client, userdata, level, buf):
    print("pub log:"+buf)

def sub_log(client, userdata, level, buf):
    print("sub log:"+buf)

client = mqtt.Client( clean_session=args.clean_session, client_id=args.clientid, protocol=mqtt.MQTTv311 )
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

if args.post_broker != None:
    pub = urllib.parse.urlparse(args.post_broker)
    if pub.username != None: 
        post_client.username_pw_set( pub.username, pub.password )

    post_client.connect( pub.hostname )

    print('ready to post to %s as %s' % ( pub.hostname, pub.username ))

client.loop_forever()



