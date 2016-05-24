#!/bin/bash

set -e

if [[ $# != 1 && $# != 2 ]]
then
    echo "You should set the branch / revision!"
    exit 1
fi

TMPDIR_BRANCH=/tmp/tmp_branch

rm -rf server/*
rm -rf $TMPDIR_BRANCH || true

if [[ $# == 1 ]]
then
    bzr checkout --lightweight $1 $TMPDIR_BRANCH
else
    bzr checkout --lightweight -r $2 $1 $TMPDIR_BRANCH
fi


cp -R $TMPDIR_BRANCH/* server/

