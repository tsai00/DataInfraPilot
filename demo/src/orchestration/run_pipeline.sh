#!/bin/bash

# Usage: ./run_pipeline.sh sreality rent 20250608

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

if [ -z "$1" ]
  then
    echo 'No project name provided. Choose one from [sreality, bezrealitky]'
    exit 1
else
  project=$1
fi


if [ -z "$2" ]
  then
    echo 'No listing_type provided. Choose one from [rent, sale]'
    exit 1
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


echo "Running scrape.py for project: $project, listing_type: $listing_type, batch_id: $batchid"
python3 "$SCRIPT_DIR/scrape.py" --project "$project" --listing-type "$listing_type" --batch-id "$batchid"
if [ $? -ne 0 ]; then echo "Error: scrape.py failed."; exit 1; fi # Check last command's exit status

echo "Running transform.py..."
python3 "$SCRIPT_DIR/transform.py" --project "$project" --listing-type "$listing_type" --batch-id "$batchid"
if [ $? -ne 0 ]; then echo "Error: transform.py failed."; exit 1; fi

echo "Running upload_to_db.py..."
python3 "$SCRIPT_DIR/upload_to_db.py" --project "$project" --listing-type "$listing_type" --batch-id "$batchid"
if [ $? -ne 0 ]; then echo "Error: upload_to_db.py failed."; exit 1; fi

echo "Pipeline finished successfully."