#!/bin/bash
set -e

git --git-dir /tmp/gcloud_history//google-cloud-sdk push origin head --tags
echo "git sync complete"
