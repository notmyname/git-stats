#!/bin/sh

sort -t: -n -k 2 ./percent_active.data | tail -20
