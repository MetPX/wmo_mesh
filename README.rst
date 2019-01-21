
Status: Work in progress (ie. not functional at all yet.)

==================================================
Minimal Demonstration of Mesh network over Pub/Sub
==================================================

Inform peers who subscribe about data made available in a well understood
common tree. Peers download data announced by others, and re-announce 
in turn for their subscribers.

What is the Mesh?  

* A reasonable subset peers may operate brokers to publish and subscribe to each other.  

* when a peer announces a message, it looks for the file in its tree.
  If it is there, it compares the checksum to the one announced.

* each one downloads data it does not already have (different checksums)
  from peer brokers, and announces those downloads locally for other peers.

* peers who feel data is too *late* just add subscriptions to more peers.
  and/or run multiple mesh_peer.py processes to the same peer (sharing the client_id) 

As long as there is at least one transitive path between all peers, 
all peers will get all data.

This demonstration is done with MQTT protocol which is more
interoperable than the more robust AMQP protocol. It is intended
to demonstrate the algorithm and the method, not for production use.

Security has not been thoroughly examined yet. In this version everyone
copies everything from everyone else.

The message format used is a minimal subset with the same semantics
as the one in use a few years in `Sarracenia <https://github.com/MetPX/sarracenia>`_
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

   This is chosen rather than any sort of epochal second cound for readability
   and to avoid worrying about leap seconds.

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


start management gui on host:18083

add users, guest and owner, and set their passwords.
Add the following to /etc/emqx/acl.conf::

 {allow, all, subscribe, [ "xpublic/#" ] }.

 {allow, {user, "owner"}, publish, [ "xpublic/#" ] }.

then just restart::

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


cleanup
~~~~~~~

a sample cron job for directory cleanup has been included.  It is called as follows::

    ./old_hour_dirs.py 13 data

to remove all directories with utc datestamps more than 13 hours old.



Insert Some Data
----------------

There are some Canadian data pumps publishing Sarracenia v02 messages over AMQP 0.9 protocol
(rabbitMQ broker) available on the internet.  there are various ways of injecting data
into such a network, using the exp_2mqtt for a Sarracenia subscriber.
