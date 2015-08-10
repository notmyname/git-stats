#!/bin/bash

echo "Open Patches Stats:"
./patches_parser.py swift-open.patches

echo
echo

echo "Closed Patches Stats:"
./patches_parser.py swift-closed.patches


echo
echo

echo "Total Patches Stats:"
./patches_parser.py swift-closed.patches swift-open.patches
