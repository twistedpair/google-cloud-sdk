#!/bin/bash
set -e

git push --quiet origin head --tags
echo "git sync complete"
