#!/bin/bash

# Check for correct number of arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 sourcefile.txt myfortune.dat"
    exit 1
fi

# Assign command-line arguments to variables
SOURCE_FILE="$1"
TARGET_DAT="${2%.*}.dat"  # Ensure the target file has a .dat extension
TEMP_FILE="${SOURCE_FILE%.*}_temp.txt"  # Temporary file for preprocessing

# Check if the source file exists
if [ ! -f "${SOURCE_FILE}" ]; then
    echo "Error: The file ${SOURCE_FILE} does not exist."
    exit 1
fi

# Preprocess the file to ensure each joke is separated by a '%'
# Assuming each joke ends with a '.' followed by a newline
awk 'BEGIN{ORS=""} /.$/{print $0 "%\n"; next} {print $0 "\n"}' "${SOURCE_FILE}" > "${TEMP_FILE}"

# Use strfile to create the .dat file for fortune
strfile "${TEMP_FILE}" "${TARGET_DAT}"

# Check if strfile succeeded
if [ $? -eq 0 ]; then
    echo "Success: ${TARGET_DAT} created."
    # Optionally, remove the temporary file
    rm "${TEMP_FILE}"
else
    echo "Error: Failed to create ${TARGET_DAT}."
    exit 1
fi
