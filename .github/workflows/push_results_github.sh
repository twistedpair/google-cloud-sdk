#!/bin/bash
set -eu

echo "Switch to checkout path"
cd  /tmp/gcloud_history/

echo "Setup push token"
git remote set-url origin https://${GITHUB_PUSH_TOKEN}@github.com/twistedpair/google-cloud-sdk.git

echo "Push tags and commits..."
git pull origin master --verbose
git push -u origin master --tags --verbose

git log --graph --oneline --decorate --all
echo "git sync complete"
