#!/bin/sh

HERE=`pwd`

cd /Users/john/Documents/python-swiftclient/
git shortlog -nes >${HERE}/client_vcs_authors
cd ${HERE}
python ./authors.py ${HERE}/client_vcs_authors /Users/john/Documents/python-swiftclient/AUTHORS
