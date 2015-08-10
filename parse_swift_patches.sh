#!/bin/bash

echo "Open Patches Stats:"
./patches_parser.py swift-open.patches

echo
echo

echo "Closed Patches Stats:"
./patches_parser.py swift-closed.patches
