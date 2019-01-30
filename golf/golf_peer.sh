#!/bin/bash

 mosquitto_sub -h bwqd -u guest -P guestpw -q 1 -t 'xpublic/v03/post/#' | ./golf_select.py | wget -r  -i - 2>&1 | grep 'Saving to:' | sed 's+\xe2\x80\x99++' | xargs md5sum | awk ' { printf "setfattr -n user.sr_sum -v d,%s %s\n", $1, $2;   }' | sh -x 2>&1  | ./golf_pub.py

