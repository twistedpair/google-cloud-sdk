#!/bin/bash
set -e

# Fixes for malformed release notes
declare -A MISSING_RELEASE_DATES_FIXES=(
  ["113.0.0"]="2016-06-08" \
  ["154.0.1"]="2017-05-04" \
 )

COMMIT_AUTHOR="Google <gcloud@google.com>" # TODO who really authors these?

REPO_URI="https://github.com/twistedpair/google-cloud-sdk.git"
WORK_DIR=/tmp/gcloud_history
GIT_WORK_DIR="$WORK_DIR/google-cloud-sdk"

# In case you're new here
if [[ ! -e $WORK_DIR ]]; then
    echo "Making initial checkout"
    git clone --quiet $REPO_URI $WORK_DIR
fi

cd $WORK_DIR

echo "Syncing from master"
git checkout master
git pull origin master

process_sdk_release()
{
    RELEASE_VERSION=$1

    echo "Processing $RELEASE_VERSION"

    ## Download each
    ARTIFACT_NAME="google-cloud-sdk-$RELEASE_VERSION-linux-x86_64.tar.gz"
    echo -e "\tDownloading..."
    gsutil -mq cp "gs://cloud-sdk-release/$ARTIFACT_NAME" .
    
    echo -e "\tExtracting..."
    tar -xf ${ARTIFACT_NAME}

    ## Extract date from release notes
    # dates are also in GCS metadata, but not accurate
    RELEASE_DATE=`grep -Po "## $RELEASE_VERSION \(\K\d{4}.\d{1,2}.\d{1,2}(?=\))" google-cloud-sdk/RELEASE_NOTES`
    #grep -Po "## \d+\.\d+\.\d+(\.\d+)? \(\K\d{4}.\d{1,2}.\d{1,2}(?=\))" /opt/gcloud/google-cloud-sdk/RELEASE_NOTES

    if [ -z $RELEASE_DATE ]; then
        
        # Fix bugs in bad releases using corrections
        # TODO use look ahead (next release) to find the correctly updated manifest. Fail on bad pass, fix on next pas.
        RELEASE_DATE_FIX=${MISSING_RELEASE_DATES_FIXES[$RELEASE_VERSION]}
        if [ -z RELEASE_DATE_FIX ]; then
            echo -e "\tCannot find release date for $RELEASE_VERSION"    
            exit 1
        else
            echo -e "\tUsing missing date lookup map for correction, $RELEASE_DATE_FIX"
            RELEASE_DATE=$RELEASE_DATE_FIX
        fi
    fi
    
    FULL_RELEASE_DATE="$RELEASE_DATE 00:00:00Z"

    ## Copy into our git repo folder
    # Note: lots of Python libs get bundled in here. Don't grab all of them, just the gcloud libs
    git add \
        google-cloud-sdk/lib/googlecloudsdk/ \
        google-cloud-sdk/lib/google/ \
        google-cloud-sdk/README \
        google-cloud-sdk/RELEASE_NOTES \
        google-cloud-sdk/LICENSE \
        google-cloud-sdk/properties \
        google-cloud-sdk/*.inc \
        google-cloud-sdk/*.sh \
        google-cloud-sdk/*.bat

    ## Make a commit using the --date flag and the above extracted date
    echo -e "\tCommitting..."
    git commit \
        -m "$RELEASE_VERSION release" \
        --date "$FULL_RELEASE_DATE" \
        --author "\'$COMMIT_AUTHOR\'" \
        --no-gpg-sign \
        --quiet \
        --no-verify
    
    git tag $RELEASE_VERSION

    # Cleanup
    echo -e "\tCleaning..."
    rm ${ARTIFACT_NAME}
}

## List all packages in repo
# list all release versions in repo
# ensure sorted, so we start with oldest
SDK_VERSIONS=$(gsutil ls gs://cloud-sdk-release/  | grep -Po "\d+\.\d+\.\d+(\.\d+)?(?=-linux-x86_64)" | sort -n)

for RELEASE_VERSION in $SDK_VERSIONS; do
    VERSION_TAG_RESULT=`git tag -l $RELEASE_VERSION`

    ## Exclude all versions we already have tags for
    if [ -z $VERSION_TAG_RESULT ]
    then
        process_sdk_release $RELEASE_VERSION
    else
    echo "Skipping $RELEASE_VERSION, already tagged"
fi
done

# TODO git push origin master
