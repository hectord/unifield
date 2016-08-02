#!/bin/bash

set -e

if [[ $# != 2 && $# != 3 ]]
then
    echo "You should set the name (web or server), the branch and (optionally), the revision!"
    exit 1
fi

TMPDIR_BRANCH=/tmp/tmp_branch

rm -rf $1/*
rm -rf $TMPDIR_BRANCH || true

if [[ $# == 2 ]]
then
    bzr checkout --lightweight $2 $TMPDIR_BRANCH
else
    bzr checkout --lightweight -r $3 $2 $TMPDIR_BRANCH
fi


cp -R $TMPDIR_BRANCH/* $1/

