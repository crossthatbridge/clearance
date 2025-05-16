#!/bin/bash
set -e

# Load environment variables from .envrc file
[ -f .envrc ] && source .envrc
export AWS_DEFAULT_REGION=us-east-1

# Load VPC resources
source workspace-resources.txt

# Directory configuration
DIRECTORY_NAME="clearance.local"
DIRECTORY_PASSWORD=${PASSWORD:-"PLEASE_SET_PASSWORD_IN_ENVRC"}
DIRECTORY_SIZE="Small" # Small is suitable for up to 500 users

echo "Creating Simple AD directory..."
DIRECTORY_ID=$(aws ds create-directory \
  --name $DIRECTORY_NAME \
  --password $DIRECTORY_PASSWORD \
  --size $DIRECTORY_SIZE \
  --vpc-settings "VpcId=$VPC_ID,SubnetIds=[$PUBLIC_SUBNET_ID,$PRIVATE_SUBNET_ID]" \
  --query 'DirectoryId' \
  --output text)

echo "Directory creation initiated: $DIRECTORY_ID"
echo "Waiting for directory to become active (this may take 15-20 minutes)..."

# Wait for the directory to become active by polling
while true; do
  STATUS=$(aws ds describe-directories \
    --directory-ids $DIRECTORY_ID \
    --query 'DirectoryDescriptions[0].Stage' \
    --output text)
  
  echo "Current status: $STATUS"
  
  if [ "$STATUS" == "Active" ]; then
    break
  fi
  
  echo "Waiting for directory to become active... (this may take several minutes)"
  sleep 60
done

echo "Directory is now active!"

# Save the directory ID to the resources file
echo "DIRECTORY_ID=$DIRECTORY_ID" >> workspace-resources.txt
echo "DIRECTORY_NAME=$DIRECTORY_NAME" >> workspace-resources.txt

echo "Directory setup completed successfully!" 