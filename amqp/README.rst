
====================================
WMO Mesh demonstration with RabbitMQ
====================================

.. contents::

STATUS
======

20190302 - working if you check out Sarracenia from git.  No packages available yet.


Introduction
============

Implement the wmo mesh algorithm using Sarracenia, which is an application
that uses the RabbitMQ AMQP broker. Interoperabilty among AMQP brokers is
non-trivial, so we specify RabbitMQ.

The steps are:

* Install a local rabbitMQ broker, with a feeder user (able to post to any exchange.)
  and a reader user (convention: anonymous, can subscribe but cannot post.)

* install a web server to serve the downloaded clone of data from a peer.

* install Sarracenia.

* create configurations for two or more peers.


Install Web Server
==================

steps::

   apt install webfsd
   mkdir /tmp/WMO_AMQP_sketch
   cd /tmp/WMO_AMQP_sketch
   webfs -p 8081


Install Sarracenia
==================

.. NOTE: this is currently (2019/03/02) a lie!
   There are some fixes in the git repo, so one would need either
   to clone that, or wait until the next version exists >= 2.19.03


To be ready for rabbitmq broker setup::

   sudo apt install python3-paramiko
   sudo apt install metpx-sarracenia

   mkdir ~/.config ~/.config/sarra ~/.config/sarra/subscribe

   cat > ~/.config/sarra/credentials.conf << EOF
   amqp://bunnymaster:bunnymasterpw@localhost/
   amqp://tfeed:tfeedpw@localhost/
   amqp://anonymous:anonymous@localhost/
   amqps://anonymous:anonymous@hpfx.collab.science.gc.ca
   amqps://anonymous:anonymous@dd.weather.gc.ca
   EOF

   cat > ~/.config/sarra/admin.conf << EOF
   admin amqp://bunnymaster@localhost/
   feeder amqp://tfeed@localhost/
   declare subscriber anonymous
   EOF





Install and Configure RabbitmQ
==============================


To get a rabbitmq-server on localhost with publisher and separate subscriber::

   sudo apt-get install rabbitmq-server

   sudo rabbitmqctl delete_user guest

   sudo rabbitmqctl add_user bunnymaster bunnymasterpw
   sudo rabbitmqctl set_permissions bunnymaster ".*" ".*" ".*"
   sudo rabbitmqctl set_user_tags bunnymaster administrator
   
   sudo rabbitmq-plugins enable rabbitmq_management

   sudo systemctl restart rabbitmq-server
   cd /usr/local/bin
   sudo wget http://localhost:15672/cli/rabbitmqadmin
   sudo chmod 755 rabbitmqadmin

   # use Sarracenia to initialize non-administrative access 
   #  and declare exchanges.
   sr_audit --users foreground


Configure Peer Subscriptions
============================

The one that is active now is::

   cp WMO_Sketch_CMC.conf ~/.config/sarra/subscribe

   sr_subscribe edit WMO_Sketch_CMC.conf

Could add another one::

   cp WMO_Sketch_Peer.conf ~/.config/sarra/subscribe/WMO_Sketch_BWQD.conf

   sr_subscribe edit WMO_Sketch_BWQD.conf

replace the file *Peer* and *ThisHost* in the file to correct values.


Start things up
===============

The commands::

  sr_subscribe start WMO_Sketch_CMC
  sr_subscribe start WMO_Sketch_BWQD

  cd ~/.cache/sarra/log

tail some log files to see what is happenning.


