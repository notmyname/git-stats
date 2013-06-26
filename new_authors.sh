#!/bin/sh

git diff $1 -- AUTHORS | grep '[+-]' | grep -v '@@' | grep -v AUTHORS
