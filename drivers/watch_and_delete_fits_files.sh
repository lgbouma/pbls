#!/bin/bash

#
# Watch the driver directory for incoming HTCondor fits files.  Delete them if
# any show up.  The need for this is connected to OSG clearing behavior.
#

# Function to delete files matching the pattern
delete_files() {
    files=(/home/ekul/proj/pbls/drivers/*fits)
    if [ ${#files[@]} -gt 0 ]; then
        echo "Deleting files matching /home/ekul/proj/pbls/drivers/*fits"
        echo /home/ekul/proj/pbls/drivers/*fits | xargs rm -f
    else
        echo "No files found matching /home/ekul/proj/pbls/drivers/*fits"
    fi
}

# Continuously watch for incoming fits files and delete them every minute
while true; do
    delete_files
    echo "Waiting for 1 minute..."
    sleep 60
done
