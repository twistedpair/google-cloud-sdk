#!/bin/bash                                                                                                                                                   
set -e                                                                                                                                                        

echo "Switch to checkout path"
cd  /tmp/gcloud_history/                                                                                                                                

echo "Setup push token"
git remote add origin https://${GITHUB_PUSH_TOKEN}@github.com/twistedpair/google-cloud-sdk.git > /dev/null 2>&1                                                        
echo "Push tags and commits..."
git pull origin master --verbose
git push -u origin master --tags --verbose                                                                                                                              
git log --graph --oneline --decorate --all 
echo "git sync complete"                                                                                                                                      
