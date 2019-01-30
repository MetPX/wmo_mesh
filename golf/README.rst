

This is a `Code Golf <https://en.wikipedia.org/wiki/Code_golf>`_ version of the demo, 
where the goal is to use the least amount of code to accomplish the goal, potentially 
at the expense of readability. Greater use of C components may make this version 
more performant than the pure python demo.

A side benefit is to illustrate the simplicity of the underlying algorithm.


Status: Work-in-Progress
------------------------

It selects, downloads, and checksums in one line of code, but it does not republish.
Unclear how to pass the other JSON fields from golf_select.py to golf_pub.py


Setup
-----

Same dependencies as the main demo plus:

sudo apt install mosquitto-clients attr

Uses golf_peer.sh to do the same job as mesh_peer.py





