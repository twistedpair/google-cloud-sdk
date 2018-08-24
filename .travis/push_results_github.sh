#!/bin/bash
set -e

cd  /tmp/gcloud_history/
git push origin head --tags
echo "git sync complete"
