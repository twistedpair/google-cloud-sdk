#!/bin/bash                                                                                                                                                   
set -e                                                                                                                                                        
                                                                                                                                                              
cd  /tmp/gcloud_history/                                                                                                                                      

echo "Push tags and commits..."
git pull origin master --verbose
git push -u origin master --tags --verbose                                                                                                                              
git log --graph --oneline --decorate --all 
echo "git sync complete"                                                                                                                                      
