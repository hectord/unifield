#!/bin/bash

if [[ -e credentials.py ]]
then
    rm credentials.py
fi
# ...
cp config.sh credentials.py

if [[ ! -e myenv ]]
then
    virtualenv myenv
    pip install -r requirements.txt
fi
source myenv/bin/activate

python restore.py

set -e
