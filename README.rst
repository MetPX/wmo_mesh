
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

*  the *relpath* is the rest of the download url.

*  The last argument is the *headers* of which there can be quite a number.
   In this minimal example, only the *sum* headers is included, giving the
   checksum of the file posted.  The first letter of the sum field designates
   a known checksum algorithm (d = MD5, s=SHA512, n=MD5 of the file name, rather than content)
   Multiple choices for checksum algorithms are offerred because some data type
   may have equivalent but not binary identical representations.

   For use cases where full mirroring is desired, additional headers indicating
   permission modes, modification times, etc.. may be included.


Create a Peer
=============

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

- sudo bash

- apt install git
- apt install vim


- apt install python3-xattr
- apt install python3-paho-mqtt  # only on ubuntu, not debian repos
- apt install python3-pip
- apt install mosquitto
- apt install python3-paho-mqtt  # available on ubuntu >18.04, but not in debian stretch

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
    # git clone https://github.com/MetPX/wmo_mesh_demo
    # cd wmo_mesh_demo
    # mkdir data


Configure Mosquitto
-------------------

    sudo bash # root shell.
    cd /etc/mosquitto
    editor /etc/mosquitto/conf.d/mesh.conf
    add::
        password_file /etc/mosquitto/pwfile

    mosquitto_passwd -c /etc/mosquitto/pwfile AWZZ
    mosquitto_passwd -c /etc/mosquitto/pwfile BWAC
    mosquitto_passwd -c /etc/mosquitto/pwfile CWAP

Configure EMQX
--------------


start management gui on host:18083

add users

   AWZZ, CWAP, BWAC, (set their passwords.)


in a shell:

    sudo bash


Start Web Servers
-----------------

    # in one shell start:
    # ./trivialserver.py

Start Peer
----------
    
   # in a shell window start:
   # ./mesh_peer.py -broker AWZZ -broker_user_name 

   in

