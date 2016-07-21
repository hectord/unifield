#!/bin/bash

set -e
. $HOME/automafield/script.sh

echo "88888888888888888888888888888888
66f490e4359128c556be7ea2d152e03b 2013-04-27 16:49:56" > server/bin/unifield-version.txt

for instance in `pct_sync_servers 0`;
do
    pct 0 $instance -c "DELETE FROM sync_server_version WHERE sum NOT IN ('88888888888888888888888888888888', '66f490e4359128c556be7ea2d152e03b')"
done

for instance in `pct_other_instances 0`;
do
    echo $instance
    pct 0 $instance -c "DELETE FROM sync_client_version WHERE sum NOT IN ('88888888888888888888888888888888', '66f490e4359128c556be7ea2d152e03b')"
done
