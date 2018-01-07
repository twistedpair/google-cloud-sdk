#!/bin/bash
set -e

ls -lRa /tmp/gcloud_history 
git --git-dir /tmp/gcloud_history//google-cloud-sdk push origin head --tags
echo "git sync complete"
