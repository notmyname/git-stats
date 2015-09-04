#!/bin/sh

HERE=`pwd`

cd /Users/john/Documents/swift/
git shortlog -nes >${HERE}/vcs_authors
cd ${HERE}
python ./authors.py ${HERE}/vcs_authors /Users/john/Documents/swift/AUTHORS
