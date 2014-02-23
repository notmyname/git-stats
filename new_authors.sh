#!/bin/sh

HERE=`pwd`

cd /Users/john/Documents/swift/
git shortlog --no-merges -nes >${HERE}/vcs_authors
cd ${HERE}
python ./authors.py
