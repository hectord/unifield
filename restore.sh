#!/bin/bash

set -e

if [[ -e credentials.py ]]
then
    rm credentials.py
fi
# ...
cp config.sh credentials.py

if [[ ! -e myenv ]]
then
    virtualenv myenv
fi

source myenv/bin/activate
pip install -r requirements.txt

python restore.py

set -e

