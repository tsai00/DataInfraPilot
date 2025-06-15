#!/bin/bash

# Usage: ./run_pipeline.sh sreality rent 20250608

if [ -z "$1" ]
  then
    echo 'No project name provided. Choose one from [sreality, bezrealitky]'
    exit 0
else
  project=$1
fi


if [ -z "$2" ]
  then
    echo 'No listing_type provided. Choose one from [rent, sale]'
    exit 0
else
  listing_type=$2
fi


if [ -z "$3" ]
  then
    batchid=$(date +"%Y%m%d")
    echo 'No batch id provided, using today'
else
  batchid=$3
fi

python3 scrape.py --project $project --listing-type $listing_type --batch-id $batchid
python3 transform.py --project $project --listing-type $listing_type --batch-id $batchid
python3 upload_to_db.py --project $project --listing-type $listing_type --batch-id $batchid