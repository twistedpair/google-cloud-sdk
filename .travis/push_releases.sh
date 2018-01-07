#!/bin/bash
set -e

git --git-dir /tmp/gcloud_history push origin head --tags
echo "git sync complete"
