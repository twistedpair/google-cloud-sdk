#!/bin/bash
set -e

cd  /tmp/gcloud_history/
ssh-agent sh -c "ssh-add ${KEY_FILE_PATH}; git push -u origin master --tags"
echo "git sync complete"
