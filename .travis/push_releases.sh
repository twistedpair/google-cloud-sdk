#!/bin/bash
set -e

git push --quiet origin master --tags
echo "git sync complete"
