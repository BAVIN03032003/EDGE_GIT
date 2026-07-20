#!/bin/bash

echo -n "Enter GitHub Username: "
read Username
echo -n "Enter GitHub Personal Access Token (PAT): "
read -s Token
echo

echo "[INFO] Attempting to log into ghcr.io..."
echo "$Token" | docker login ghcr.io -u "$Username" --password-stdin

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Authentication stored in Docker config."
else
    echo "[ERROR] Login failed."
    exit 1
fi

unset Token
unset Username
