

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


Running
-------

Need to make some directories and symbolic links at the root of the tree to contort wget's full tree
retrieval (including hostname and the directories in baseurl) to resolve to the 
the wmo_mesh directory so the *data* directory shows up in the correct location.

examples::

    pi@AWZZ:~/wmo_mesh $ ls -lR hpfx.collab.science.gc.ca
    hpfx.collab.science.gc.ca:
    total 4
    drwxr-xr-x 2 pi pi 4096 Jan 28 00:37 ~pas037

    hpfx.collab.science.gc.ca/~pas037:
    total 0
    lrwxrwxrwx 1 pi pi 5 Jan 28 00:37 WMO_Sketch -> ../..
    pi@AWZZ:~/wmo_mesh $ 

so when wget -r downloads to hpfx.collab.science.gc.ca/~pas047/WMO_Sketch (the baseurl of the upstream
source for the demo) it ends up in the current directory, and uses the same *data/* as the original
demo.

one edits golf_peer.sh to do the same job as mesh_peer.py (there are no settings.)





