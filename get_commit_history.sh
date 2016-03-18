#!/bin/bash

(cd /Users/john/Documents/swift && git rev-list --pretty=format:"%aN|<%aE>|%aI" HEAD | grep -v commit) | ./parse_commits_into_json.py

