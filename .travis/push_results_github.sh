#!/bin/bash
set -e

cd  /tmp/gcloud_history/
git push -u origin master --tags
echo "git sync complete"
