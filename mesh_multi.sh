

if [ $# -ne 3 ]; then
   echo "usage: ./mesh_multi.sh node broker workers"
   echo "       node - hostname of node to subscribe to ( e.g. bwqd) "
   echo "       broker - node's broker url:  ( e.g. mqtt://owner:ownerpw@bwqd ) "
   echo "       workers - number of workers to share downloading"
   printf "\n example: \n\t ./mesh_multi.sh bwqd mqtt://owner:ownerpw@bwqd 5 \n"
   printf "\n should start 5 workers subscribed to messages from bwqd. \n"
   exit 1
fi

node=$1
broker=$2
workers=$3

self_broker=mqtt://owner:ownerpw@localhost

./mesh_peer.py --download no --post_exchange xdnld --post_exchange_split ${workers} --exchange xpublic --post_broker $self_broker --broker ${broker} >mesh_dispatch_${node}.log 2>&1 &

i=0
while [ $i -lt $workers ]; do
    is=`printf "%02d" $i`
    ./mesh_peer.py --inline --exchange xdnld${is} --post_exchange xpublic --post_broker $self_broker --broker ${self_broker} >mesh_worker_${is}_${node}.log 2>&1 &
    let i=${i}+1
done
