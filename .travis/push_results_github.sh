#!/bin/bash
set -e

git --git-dir /tmp/gcloud_history/.git push origin head --tags
echo "git sync complete"
