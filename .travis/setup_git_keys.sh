#!/bin/bash
set -e

# Decrypt and install GH deploy key
echo "Installing github keys..."

KEY_NAME=travis_deploy_key.private
KEY_FILE_PATH=`pwd`/.travis/$KEY_NAME
openssl aes-256-cbc -k "$GITHUB_KEY_PASSWORD" -d -a -in "$KEY_FILE_PATH.enc" -out $KEY_FILE_PATH

chmod 400 ${KEY_FILE_PATH}

echo "Setting github.com SSH key in ~/.ssh/config"
echo -e "Host github.com-twistedpair\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/id_rsa" > ~/.ssh/config

# Preaccept GH's key
echo "Installing github.com in known_hosts..."
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" > ~/.ssh/known_hosts

# Ensure we can authentica
ssh -T git@github.com
