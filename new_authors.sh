#!/bin/sh

HERE=`pwd`
PROJ_PATH="$1"

cd ${PROJ_PATH}
git shortlog -nes >${HERE}/vcs_authors
cd ${HERE}
python ./authors.py ${HERE}/vcs_authors ${PROJ_PATH}/AUTHORS
