#!/bin/bash                                                                                                                                                   
set -e                                                                                                                                                        
                                                                                                                                                              
cd  /tmp/gcloud_history/                                                                                                                                      
git remote add origin https://${GH_TOKEN}@github.com/twistedpair/google-cloud-sdk.git > /dev/null 2>&1                                                        
git push -u origin master --tags                                                                                                                              
echo "git sync complete"                                                                                                                                      
