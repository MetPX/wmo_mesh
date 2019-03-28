
====================================
WMO Mesh demonstration with RabbitMQ
====================================

.. contents::

STATUS
======

All is included in releases >= v2.19.03b5 


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

   apt install webfs
   sudo mkdir -p /var/www/html 
   sudo chown -Rv ubuntu:ubuntu /var/www/html
   sudo systemctl restart webfs


Install Sarracenia
==================

.. NOTE: this is currently (2019/03/02) a lie!
   There are some fixes in the git repo, so one would need either
   to clone that, or wait until the next version exists >= 2.19.03


To be ready for rabbitmq broker setup::

   sudo add-apt-repository ppa:ssc-hpc-chp-spc/metpx
   sudo apt update
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

   # Be warned that this command may take a while to complete (up to a couple a minutes)
   sudo systemctl restart rabbitmq-server
   cd /usr/local/bin
   sudo wget http://localhost:15672/cli/rabbitmqadmin
   sudo chmod 755 rabbitmqadmin

   # use Sarracenia to initialize non-administrative access 
   #  and declare exchanges.
   sr_audit --users foreground


Configure Peer Subscriptions
============================

This enables a subscription to the Canadian source sample AMQP server::

   sr_subscribe add WMO_mesh_CMC.conf
   sr_subscribe edit WMO_mesh_CMC.conf  # to review the configuration.

Could add a subscription to another peer::

   sr_subscribe add WMO_mesh_Peer.conf
   cd ~/.config/sarra/subscribe
   mv WMO_mesh_Peer.conf WMO_mesh_BWQD.conf
   sr_subscribe edit WMO_mesh_BWQD.conf  # to review the configuration.

replace the file *Peer* and *ThisHost* in the file to correct values.


Start things up
===============

The commands::

  sr_subscribe start WMO_mesh_CMC
  sr_subscribe start WMO_mesh_BWQD

  cd ~/.cache/sarra/log

tail some log files to see what is happenning.


