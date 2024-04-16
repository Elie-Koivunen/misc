#!/bin/bash

# Loop infinitely
while true; do echo "Current time: $(date '+%Y-%m-%d %H:%M:%S')"; filename=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 8);  touch "$filename";  echo "Created file: $filename";  sleep 5; done
