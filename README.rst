
Status: working.


==================================================
Minimal Demonstration of Mesh network over Pub/Sub
==================================================

Inform peers who subscribe to data made available in a well understood
common tree. Peers download data announced by others, and re-announce 
in turn for their subscribers.

What is the Mesh?  

* A reasonable subset of peers may operate brokers to publish and subscribe to each other.  

* when a peer announces a message, it looks for the file in its tree.
  If it is there, it compares the checksum to the one announced.

* each one downloads data it does not already have (different checksums)
  from peer brokers, and announces those downloads locally for other peers.

As long as there is at least one transitive path between all peers, 
all peers will get all data.

This demonstration is done with MQTT protocol which is more
interoperable than the more robust AMQP protocol. It is intended
to demonstrate the algorithm and the method, not for production use.

Security has not been thoroughly examined yet. In this version everyone
copies everything from everyone else.

.. contents::


Message Format
==============

The message format used is a minimal subset with the same semantics
as the one in use for a few years in `Sarracenia <https://github.com/MetPX/sarracenia>`_
The main change being a switch from AMQP-specific packing, to a
protocol agnostic JSON encoding describer here

https://github.com/MetPX/sarracenia/blob/master/doc/sr_postv3.7.rst

Entire format is human readable::

   ["20190120045018.314854383", "http://localhost/data", "bulletins/alphanumeric/20190120/UA/CWAO/04/UANT01_CWAO_200445___15103", {"sum": "d,d41d8cd98f00b204e9800998ecf8427e"}]

Boiling it down to this relatively small example makes discussion easier.

*  The *datestamp* marks when the file was posted on the first broker in the network.
   This allows easy calculcation of propagation delay across any number of nodes.
   The date format looks like a floating point number,  but is the conventional 
   YYYYMMDDHHMMSS (in UTC timezone) followed by a fraction of a second after the 
   decimal place.  

   This is chosen rather than any sort of epochal second count for readability
   and to avoid worrying about leap seconds.

   This format is essentially ISO8601 basic notation. The standard recommends
   a *T* be placed between date and time, and there is no convention to use a decimal
   marker for seconds. The use of a decimal marker allows for different users to 
   give different levels of precision (milliseconds, microseconds, etc...) without
   changing the standard. 

   In ISO8601 when times do not include a timzone marker, it is assumed to be local.
   in the meteorological domain, it seems clear the default should be UTC (Z in ISO parlance) 
   Leaving the Z out seems reasonable.

*  The *baseurl* marks the static starting point to build the complete download URL.
   it represents the root of the download tree on the remote web server.

   specifying the baseurl in each message provides a number of benefits:

   - enables third party transfer, where the broker announcing data doesn't necessarily
     have it locally, it might just know of a remote location, and not be interested in
     it for itself, but it could tell clients where to get it if they want it.

     reduces load on broker, by having other nodes do the actual transfers.

   - allows many sources of data to be mixed in the same download stream.


*  the *relpath* is the rest of the download url.

   - isolates the relative path as the basis of comparison for duplicates.


*  The last argument is the *headers* of which there can be quite a number.
   In this minimal example, only the *sum* headers is included, giving the
   checksum of the file posted.  The first letter of the sum field designates
   a known checksum algorithm (d = MD5, s=SHA512, n=MD5 of the file name, rather than content)
   Multiple choices for checksum algorithms are offerred because some data type
   may have equivalent but not binary identical representations.

   For use cases where full mirroring is desired, additional headers indicating
   permission modes, modification times, etc.. may be included.



Audience
========

This demonstration is based on the availability of multiple Linux servers, running
a recent version of Debian or Ubuntu Linux. All of the interactions are command line,
and so familiarity with linux system administration, editing of configuration files,
etc... is needed.


Peer Setup
==========


Obtain a Server:
----------------

  - for example, a raspberry pi.
    - obtain raspberry pi.
    - install base raspbian from img ( 2018-11-13-raspbian-stretch-lite.img )

    # raspi-config
    - expand file system 
    - pick keyboard layout (En US)
    - reboot

  - do network settings.
  - configure nework
  - update hostlist for actual addresses. 

any server running debian stretch is equivalent.  Ubuntu 18.04 is fine also.
Installation instructions will vary by distribution. 


things to install on debian:

- sudo apt install git vim python3-xattr python3-pip mosquitto

- sudo apt install python3-paho-mqtt  # available on ubuntu >18.04, but not in debian stretch

- use pip for what you cannot find in repositories::

   # pip3 install paho-mqtt
   Collecting paho-mqtt
     Downloading https://www.piwheels.org/simple/paho-mqtt/paho_mqtt-1.4.0-py3-none-any.whl (48kB)
       100% |████████████████████████████████| 51kB 191kB/s 
   Installing collected packages: paho-mqtt
   Successfully installed paho-mqtt-1.4.0
   root@meshC:/home/pi# 

- get the demo::

    (as an ordinary user, *root* not needed.)
    # git clone https://github.com/MetPX/wmo_mesh
    # cd wmo_mesh
    # mkdir data


Configure a Message Broker
--------------------------

A message broker of some kind needs to be configured.
The demontration only works with MQTT brokers.  One needs 
to define at least two users:

  - one subscriber (guest), able to read from xpublic/#
  - one publisher (owner), able to post to xpublic/#

Demo was done with an `EMQX <emqtt.io>`_ on a laptop, and the `mosquitto <https://mosquitto.org/>`_ running
on three raspberry pi's.  

Configure Mosquitto
~~~~~~~~~~~~~~~~~~~

    sudo editor /etc/mosquitto/conf.d/mesh.conf

    add::

        password_file /etc/mosquitto/pwfile

    then run::

       # sudo touch /etc/mosquitto/pwfile
       # sudo mosquitto_passwd -b /etc/mosquitto/pwfile owner ownerpw
       # sudo mosquitto_passwd -b /etc/mosquitto/pwfile guest guestpw
       # systemctl restart mosquitto
       # systemctl status mosquitto


Configure EMQX
~~~~~~~~~~~~~~~

(from David Podeur...)::

  here are the installation steps for EMQX on
  > Ubuntu 18.04
  > 
  > wget http://emqtt.io/downloads/latest/ubuntu18_04-deb -O emqx-ubuntu18.04-v3.0.0_amd64.deb
  > 
  > sudo dpkg -i emqx-ubuntu18.04-v3.0.0_amd64.deb
  > sudo systemctl enable emqx
  > sudo systemctl start emqx
  > 
  > URL: http://host:18083
  > Username: admin
  > Password: public

use browser to access management gui on host:18083

add users, guest and owner, and set their passwords.
Add the following to /etc/emqx/acl.conf::

 {allow, all, subscribe, [ "xpublic/#" ] }.

 {allow, {user, "owner"}, publish, [ "xpublic/#" ] }.

to have acl´s take effect, restart::

  systemctl restart emqx


Start Each Peer
---------------

each node in the network needs to run:

- a web server to allow others to download.
- a broker to allow messages to flow
- the mesh_peer script to obtain data from peers.

Start Web Servers
~~~~~~~~~~~~~~~~~~

    # in one shell start:
    # cd wmo_mesh
    # ./trivialserver.py

Start mesh_peer.py
~~~~~~~~~~~~~~~~~~
    
In a shell window on start::

   # ./mesh_peer.py -broker mqtt://guest:guestpw@peer_to_subscribe_to -post_broker mqtt://owner:ownerpw@this_host 

it will download data under the *data/* sub-directory, and publish it on this_host's broker. 

Test
~~~~

on any peer::

   # echo "hello" >data/hello.txt
   # ./mesh_pub.py --post_broker mqtt://owner:ownerpw@this_host data/hello.txt

And the file should rapidly propagate to the peers.

For example with four nodes named blacklab, awzz, bwqd, and cwnp. 
examples::
 
   blacklab% ./mesh_peer.py --broker mqtt://guest:guestpw@blacklab  --post_broker http://owner:ownerpw@awzz
   pi@BWQD:~/wmo_mesh $ ./mesh_peer.py --broker mqtt://guest:guestpw@blacklab --post_broker mqtt://owner:ownerpw@bwqd
   pi@cwnp:~/wmo_mesh $ ./mesh_peer.py --broker mqtt://guest:guestpw@bwqd --post_broker mqtt://owner:ownerpw@cwnp
   pi@AWZZ:~/wmo_mesh $ ./mesh_peer.py --broker mqtt://guest:guestpw@cwnp --post_broker mqtt://owner:ownerpw@awzz

cleanup
~~~~~~~

a sample cron job for directory cleanup has been included.  It is called as follows::

    ./old_hour_dirs.py 13 data

to remove all directories with utc datestamps more than 13 hours old.
sample crontab entry::

    21 * * * * /home/peter/wmo_mesh/old_hour_dirs.py 2 /home/peter/wmo_mesh/data

At 21 minutes past the hour, every hour delete directory trees under /home/peter/wmo_mesh/data which
are more than two hours old.


Insert Some Data
----------------

There are some Canadian data pumps publishing Sarracenia v02 messages over AMQP 0.9 protocol
(rabbitMQ broker) available on the internet. There are various ways of injecting data
into such a network, using the exp_2mqtt for a Sarracenia subscriber.

The WMO_Sketch_2mqtt.conf file is a sarracenia subscribe that subscribes to messages from
here:

   https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/

Which is an experimental data mart sandbox for use in trialling directory tree structures.
It contains an initial tree proposal. The data in the tree is an exposition of a UNIDATA-LDM
feed used as a quasi-public academic feed for North American universities training meteorologists.
It provides a good facsimile of what a WMO data exchange might look like, in terms of volume
and formats. Certain voluminous data sets have been elided from the feed, to ease
experimentation.

1. `Install Sarracenia <https://github.com/MetPX/sarracenia/blob/master/doc/Install.rst>`_

2. Ensure configuration directories are present::

      mkdir ~/.config ~/.config/sarra ~/.config/sarra/subscribe ~/.config/sarra/plugins
      # add credentials to access AMQP pumps.
      echo "amqps://anonymous:anonymous@hpfx.collab.science.gc.ca" >~/.config/sarra/credentials.conf
      echo "amqps://anonymous:anonymous@dd.weather.gc.ca" >>~/.config/sarra/credentials.conf
 
2. copy configs present only in git repo, and no released version

   recipe::

     cd ~/.config/sarra/plugins
     wget https://raw.githubusercontent.com/MetPX/sarracenia/master/sarra/plugins/exp_2mqtt.py
     cd ~/.config/sarra/subscribe
     wget https://raw.githubusercontent.com/MetPX/sarracenia/master/sarra/examples/subscribe/WMO_Sketch_2mqtt.conf

   As of this writing, the above is only in the git repository. in later versions of Sarracenia ( > 2.19.01b1),
   the configurations will be included in examples, so one could replace the above with:

   sr_subscribe add WMO_Sketch_2mqtt.conf
    

   what is in the WMO_Sketch_2mqtt.conf file?::

    broker amqps://anonymous@hpfx.collab.science.gc.ca   <-- connect to this broker as anonymous user.
    exchange xs_pas037_wmosketch_public                  <-- to this exchange (root topic in MQTT parlance)
    no_download                                          <-- only get messages, data download will by done
                                                             by mesh_peer.py
    exp_2mqtt_post_broker mqtt://tsource@localhost       <-- tell plugin the MQTT broker to post to.
    post_exchange xpublic                                <-- tell root of the topic tree to post to.
    plugin exp_2mqtt                                     <-- plugin that connects to MQTT instead of AMQP
    subtopic #                                           <-- server-side wildcard to say we are interested in everything.
    accept .*                                            <-- client-side wildcard, selects everything.
    report_back False                                    <-- do not return telemetry to source.


3. Start up the configuration.

   for an initial check, do a first start up of the message transfer client::

       sr_subscribe foreground WMO_Sketch_2mqtt.conf

   After runing for a few seconds, hit ^C to abort. Then start it again in daemon mode::

       sr_subscribe start WMO_Sketch_2mqtt.conf

   and it should be running... logs in ~/.config/sarra/log

   Sample output::

       blacklab% sr_subscribe foreground WMO_Sketch_2mqtt.conf  
       2019-01-22 19:43:46,457 [INFO] sr_subscribe WMO_Sketch_2mqtt start
       2019-01-22 19:43:46,457 [INFO] log settings start for sr_subscribe (version: 2.19.01b1):
       2019-01-22 19:43:46,458 [INFO] 	inflight=.tmp events=create|delete|link|modify use_pika=False topic_prefix=v02.post
       2019-01-22 19:43:46,458 [INFO] 	suppress_duplicates=False basis=path retry_mode=True retry_ttl=300000ms
       2019-01-22 19:43:46,458 [INFO] 	expire=300000ms reset=False message_ttl=None prefetch=25 accept_unmatch=False delete=False
       2019-01-22 19:43:46,458 [INFO] 	heartbeat=300 sanity_log_dead=450 default_mode=000 default_mode_dir=775 default_mode_log=600 discard=False durable=True
       2019-01-22 19:43:46,458 [INFO] 	preserve_mode=True preserve_time=True realpath_post=False base_dir=None follow_symlinks=False
       2019-01-22 19:43:46,458 [INFO] 	mirror=False flatten=/ realpath_post=False strip=0 base_dir=None report_back=False
       2019-01-22 19:43:46,458 [INFO] 	Plugins configured:
       2019-01-22 19:43:46,458 [INFO] 		do_download: 
       2019-01-22 19:43:46,458 [INFO] 		do_get     : 
       2019-01-22 19:43:46,458 [INFO] 		on_message: EXP_2MQTT 
       2019-01-22 19:43:46,458 [INFO] 		on_part: 
       2019-01-22 19:43:46,458 [INFO] 		on_file: File_Log 
       2019-01-22 19:43:46,458 [INFO] 		on_post: Post_Log 
       2019-01-22 19:43:46,458 [INFO] 		on_heartbeat: Hb_Log Hb_Memory Hb_Pulse RETRY 
       2019-01-22 19:43:46,458 [INFO] 		on_report: 
       2019-01-22 19:43:46,458 [INFO] 		on_start: EXP_2MQTT 
       2019-01-22 19:43:46,458 [INFO] 		on_stop: 
       2019-01-22 19:43:46,458 [INFO] log_settings end.
       2019-01-22 19:43:46,459 [INFO] sr_subscribe run
       2019-01-22 19:43:46,459 [INFO] AMQP  broker(hpfx.collab.science.gc.ca) user(anonymous) vhost()
       2019-01-22 19:43:46,620 [INFO] Binding queue q_anonymous.sr_subscribe.WMO_Sketch_2mqtt.24347425.16565869 with key v02.post.# from exchange xs_pas037_wmosketch_public on broker amqps://anonymous@hpfx.collab.science.gc.ca
       2019-01-22 19:43:46,686 [INFO] reading from to anonymous@hpfx.collab.science.gc.ca, exchange: xs_pas037_wmosketch_public
       2019-01-22 19:43:46,687 [INFO] report_back suppressed
       2019-01-22 19:43:46,687 [INFO] sr_retry on_heartbeat
       2019-01-22 19:43:46,688 [INFO] No retry in list
       2019-01-22 19:43:46,688 [INFO] sr_retry on_heartbeat elapse 0.001044
       2019-01-22 19:43:46,689 [ERROR] exp_2mqtt: authenticating as tsource 
       2019-01-22 19:43:48,101 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/KWNB/SX, body=["20190123004338.097888", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/KWNB/SX/SXUS22_KWNB_230000_RRX_e12080ee6aaf254ab0cd97069be3812b.txt", {"parts": "1,278,1,0,0", "atime": "20190123004338.0927228928", "mtime": "20190123004338.0927228928", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,e12080ee6aaf254ab0cd97069be3812b", "mode": "664"}]
       2019-01-22 19:43:48,119 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/KOUN/US, body=["20190123004338.492952", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/KOUN/US/USUS44_KOUN_230000_4d4e58041d682ad6fe59ca9410bb85f4.txt", {"parts": "1,355,1,0,0", "atime": "20190123004338.488722801", "mtime": "20190123004338.488722801", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,4d4e58041d682ad6fe59ca9410bb85f4", "mode": "664"}]
       2019-01-22 19:43:48,136 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/KWNB/SM, body=["20190123004338.052487", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/KWNB/SM/SMVD15_KWNB_230000_RRM_630547d96cf1a4f530bd2908d7bfe237.txt", {"parts": "1,2672,1,0,0", "atime": "20190123004338.048722744", "mtime": "20190123004338.048722744", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,630547d96cf1a4f530bd2908d7bfe237", "mode": "664"}]
       2019-01-22 19:43:48,152 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/KWNB/SO, body=["20190123004338.390638", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/KWNB/SO/SOVD83_KWNB_230000_RRX_8e94b094507a318bc32a0407a96f37a4.txt", {"parts": "1,107,1,0,0", "atime": "20190123004338.388722897", "mtime": "20190123004338.388722897", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,8e94b094507a318bc32a0407a96f37a4", "mode": "664"}]
       2019-01-22 19:43:48,170 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/EGRR/IU, body=["20190123004331.855253", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/EGRR/IU/IUAA01_EGRR_230042_99240486f422b0cb2dcead7819ba8100.bufr", {"parts": "1,249,1,0,0", "atime": "20190123004331.852722168", "mtime": "20190123004331.852722168", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,99240486f422b0cb2dcead7819ba8100", "mode": "664"}]
       2019-01-22 19:43:48,188 [INFO] exp_2mqtt publising topic=xpublic/v03/post/2019012300/CWAO/FT, body=["20190123004337.955676", "https://hpfx.collab.science.gc.ca/~pas037/WMO_Sketch/", "/2019012300/CWAO/FT/FTCN31_CWAO_230000_AAA_81bdc927f5545484c32fb93d43dcf3ca.txt", {"parts": "1,182,1,0,0", "atime": "20190123004337.952722788", "mtime": "20190123004337.952722788", "source": "UCAR-UNIDATA", "from_cluster": "DDSR.CMC,DDI.CMC,DDSR.SCIENCE,DDI.SCIENCE", "to_clusters": "DDI.CMC,DDSR.CMC,DDI.SCIENCE,DDI.SCIENCE", "sum": "d,81bdc927f5545484c32fb93d43dcf3ca", "mode": "664"}]
    
   As these messages come from Sarracenia, they include a lot more fields. There is also a feed from 
   the current Canadian datamart which has a more eclectic mix of data, but not much in WMO formats:

        https://raw.githubusercontent.com/MetPX/sarracenia/master/sarra/examples/subscribe/dd_2mqtt.conf

   there will be imagery and Canadian XML's and in a completely different directory tree that is much more difficult
   to clean.

4. Does it work?

   Hard to tell. If you set up passwordless ssh between the nodes, you can generate some gross level reports like so::

      blacklab% for i in blacklab awzz bwqd cwnp; do ssh $i du -sh wmo_mesh/data/*| awk ' { printf "%10s %5s %s\n", "'$i'", $1, $2 ; };' ; done | sort -r -k 3
          cwnp   31M wmo_mesh/data/2019012419
          bwqd   29M wmo_mesh/data/2019012419
      blacklab   29M wmo_mesh/data/2019012419
          awzz   29M wmo_mesh/data/2019012419
          cwnp   29M wmo_mesh/data/2019012418
          bwqd   28M wmo_mesh/data/2019012418
      blacklab   28M wmo_mesh/data/2019012418
          awzz   28M wmo_mesh/data/2019012418
          cwnp   32M wmo_mesh/data/2019012417
          bwqd   32M wmo_mesh/data/2019012417
      blacklab   31M wmo_mesh/data/2019012417
          awzz   32M wmo_mesh/data/2019012417
      blacklab%

   So, not perfect... well that's how things are right now...


Demo Limitations 
================

* **Retrievel is http or https only** not SFTP, or ftp, or ftps. (Sarracenia does all of them.)

* **volume limited to what can be handled by a single process.** Sarracenia *instances* option allows 
  use of arbitrary number of workers to share downloads, higher aggregate performance 
  with less management.

* **if urlretrieve fails the demo dies**. Sarracenia has extensive logic to tolerate and recover
  gracefully without spamming the source, and while preferring newer data to missing old data.

* **The same tree everywhere.** Sarracenia has extensive support for transforming the tree on the fly.

* **No broker management.** Sarracenia incorporates user permissions management of a rabbitmq broker,
  so the broker can be entirely managed, after initial setup, with the application. it implements
  a flexible permission scheme that is onerous to do manually.
  In the demo, access permissions must be done manually. 

* **please supply real web server** demo uses python web server whose sole virtue is simplicity.  
  For deployment, a real web server, such as apache, or nginx is recommended.

* **anyone can share any data from anywhere** demo allows any node to post data anywhere in the tree.
  It is a deployment detail that some countries will want to restrict who can post on whose behalf.
  an example basis of such restriction is the *select* argument. allowing one to allow only
  certain parts of the tree to come from certain peers, if that is desired.

  One could build a worldwide list, shared among WMO partners, of which node is allowed to originate
  data for a given CCCC.  One could also 
  
* **credentials in command-line** better practice to put them in a separate file, as Sarracenia does.


