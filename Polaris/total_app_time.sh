#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_data_directory>"
    exit 1
fi

DIRECTORY="$1"

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Provided path is not a directory"
    exit 1
fi

total_sum=0

get_max_time() {
    local start=$1
    local end=$2
    local max_time=0

    for ((i=$start; i<$end; i++)); do
        folder="$DIRECTORY/$i"

        if [[ -d "$folder" && -f "$folder/job.out" ]]; then
            time_value=$(grep "Time for full app Time:" "$folder/job.out" | awk -F ': ' '{print $2}' | awk -F ' sec' '{print $1}')

            # If time_value is empty or not a number, skip the iteration
            if [[ -z "$time_value" || ! "$time_value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
                echo "Warning: Invalid time value found in $folder/job.out or the expected pattern is missing."
                continue
            fi
            
            if (( $(echo "$time_value > $max_time" | bc -l) )); then
                max_time=$time_value
            fi
        else
            echo "Warning: Folder $folder or $folder/job.out not found."
        fi
    done

    echo "$max_time"
}

for start in 1 50 100 150; do
    end=$((start + 50))
    if [ "$end" -gt 193 ]; then
        end=193
    fi
    max_time=$(get_max_time $start $end)

    # If max_time is empty or not a number, skip the addition
    if [[ -z "$max_time" || ! "$max_time" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "Warning: Invalid max time computed for range $start to $end. Skipping this set."
        continue
    fi

    total_sum=$(echo "$total_sum + $max_time" | bc -l)
done

echo "Total Sum of Max Times: $total_sum seconds"
