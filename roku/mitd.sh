#!/bin/bash
if [ $1 -eq 0 ]
  then
    echo "Password should be the first argument."
fi
APPNAME=mitd
ROKU_DEV_TARGET=roku.lan
ROKU_DEV_TARGET=192.168.1.102
USER=rokudev
PASS=$1
rm $APPNAME.zip
cd $APPNAME
zip -r ../$APPNAME.zip *
cd ..
echo "Installing $APPNAME to host $ROKU_DEV_TARGET"
curl --anyauth -u $USER:$PASS -s -S -F "mysubmit=Replace" -F "archive=@$(pwd)/$APPNAME.zip" -F "passwd=" http://$ROKU_DEV_TARGET/plugin_install
