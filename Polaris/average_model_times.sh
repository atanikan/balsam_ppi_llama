#!/bin/bash

# Check if directory path is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_directory>"
    exit 1
fi

DIRECTORY="$1"

# Check if provided path is a directory
if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Provided path is not a directory"
    exit 1
fi

# Initialize variables to store the sum of all initialization times, iteration times, and full app times
total_init_time=0
total_iter_time=0
total_app_time=0
count_init=0
count_iter=0
count_app=0

# Use find to recursively search for files named "job.out" and process each one
while IFS= read -r file; do
    # Check for "Time for model initialisation" and accumulate its time
    if grep -q "Time for model initialisation" "$file"; then
        init_time_value=$(grep "Time for model initialisation" "$file" | awk -F 'Time: ' '{print $2}' | awk -F ' sec' '{print $1}')
        total_init_time=$(echo "$total_init_time + $init_time_value" | bc -l)
        count_init=$((count_init+1))
    fi

    # Check for "Iteration: 0, Time:" and accumulate its time
    if grep -q "Iteration: 0, Time:" "$file"; then
        iter_time_value=$(grep "Iteration: 0, Time:" "$file" | awk -F 'Time: ' '{print $2}' | awk -F ' sec' '{print $1}')
        total_iter_time=$(echo "$total_iter_time + $iter_time_value" | bc -l)
        count_iter=$((count_iter+1))
    fi

    # Check for "Time for full app Time:" and accumulate its time
    if grep -q "Time for full app Time:" "$file"; then
        app_time_value=$(grep "Time for full app Time:" "$file" | awk -F 'Time: ' '{print $2}' | awk -F ' sec' '{print $1}')
        total_app_time=$(echo "$total_app_time + $app_time_value" | bc -l)
        count_app=$((count_app+1))
    fi
done < <(find "$DIRECTORY" -name "job.out" -type f)

# Calculate and display the average initialization time
if [ "$count_init" -gt 0 ]; then
    average_init_time=$(echo "$total_init_time / $count_init" | bc -l)
    echo "Average Time for Model Initialisation: $average_init_time seconds"
else
    echo "No 'job.out' files found with 'Time for model initialisation'"
fi

# Calculate and display the average time for one iteration
if [ "$count_iter" -gt 0 ]; then
    average_iter_time=$(echo "$total_iter_time / $count_iter" | bc -l)
    echo "Average Time for 1 Iteration: $average_iter_time seconds"
else
    echo "No 'job.out' files found with 'Iteration: 0, Time:'"
fi

# Calculate and display the average time for full app
if [ "$count_app" -gt 0 ]; then
    average_app_time=$(echo "$total_app_time / $count_app" | bc -l)
    echo "Average Time for Full App: $average_app_time seconds"
else
    echo "No 'job.out' files found with 'Time for full app Time:'"
fi
