#!/bin/bash

if [ -z ${2+x} ]; then
 echo "usage: $0 where-to-connect port";
 exit;
else
 HOST=$1
 PORT=$2
 PSWD=osboxes.org

 ssh -p ${PORT} -o PubkeyAuthentication=no ${HOST} 'echo ${PSWD} | sudo -S -- sh -c "echo \"ACCEPT_KEYWORDS=\\\"~amd64\\\"\" >> /etc/portage/make.conf"'
 scp -o PubkeyAuthentication=no -P ${PORT}  -r guest/*  ${HOST}:
fi