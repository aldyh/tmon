#!/bin/sh
# Set up the tmon demo on a DreamHost shared-hosting account.
# Run this from the site directory after extracting the tarball.
#
# Example:
#     cd ~/tmon.example.com
#     tar xzf tmon-demo.tar.gz
#     sh setup-demo.sh

set -e

echo "Creating virtualenv..."
python3 -m venv .venv
echo "Installing Flask..."
.venv/bin/pip install --quiet flask

mkdir -p public tmp

echo "Restarting Passenger..."
touch tmp/restart.txt

echo "Done.  The site should be live."
