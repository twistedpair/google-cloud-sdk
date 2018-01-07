#!/bin/bash
set -e

# TODO move repo location to build ENV var
git remote add origin https://${GH_ACCESS_TOKEN}@github.com/twisedpair/google-cloud-sdk.git
git push --quiet --set-upstream origin master 
