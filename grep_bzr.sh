#!/bin/bash

set -e

if [[ $# != 1 ]]
then
    echo "You should set the branch!"
    exit 1
fi

TMPDIR_BRANCH=/tmp/tmp_branch

rm -rf server/*
rm -rf $TMPDIR_BRANCH || true

bzr checkout --lightweight lp:~fabien-morin/unifield-server/perf_improvement_merged $TMPDIR_BRANCH

cp -R $TMPDIR_BRANCH/* server/

