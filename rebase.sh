#!/bin/bash

set -e

if [[ $# == 0 ]]
then
    echo "You have to specify the database to upgrade" >&2
    exit 1
fi

for db in $@
do
    ./launch_server.sh -u base --stop-after-init -d $db
done

