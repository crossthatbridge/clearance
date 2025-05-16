#!/bin/bash
set -e

# Load environment variables from .envrc file
[ -f .envrc ] && source .envrc
export AWS_DEFAULT_REGION=us-east-1

# Load resources
source workspace-resources.txt

echo "Registering directory with WorkSpaces..."
aws workspaces register-directory \
  --directory-id $DIRECTORY_ID \
  --enable-work-docs false \
  --enable-self-service false \
  --subnet-ids $PRIVATE_SUBNET_ID $PUBLIC_SUBNET_ID

echo "Waiting for directory registration to complete..."
REGISTRATION_STATUS="REGISTERING"
while [ "$REGISTRATION_STATUS" != "REGISTERED" ]; do
  REGISTRATION_STATUS=$(aws workspaces describe-workspace-directories \
    --directory-ids $DIRECTORY_ID \
    --query 'Directories[0].State' \
    --output text)
  
  echo "Registration status: $REGISTRATION_STATUS"
  
  if [ "$REGISTRATION_STATUS" == "REGISTERED" ]; then
    break
  elif [ "$REGISTRATION_STATUS" == "ERROR" ]; then
    echo "Error registering directory. Please check the AWS console for more details."
    exit 1
  fi
  
  echo "Waiting for directory registration to complete... (this may take several minutes)"
  sleep 30
done

echo "Directory registration complete!"

# Describe available bundles to find Windows 11 bundle
echo "Finding Windows 11 graphics bundle..."
BUNDLE_ID=$(aws workspaces describe-workspace-bundles \
  --owner AMAZON \
  --query "Bundles[?contains(Name, 'Graphics') && contains(Name, 'Windows 11')] | [0].BundleId" \
  --output text)

if [ -z "$BUNDLE_ID" ] || [ "$BUNDLE_ID" == "None" ]; then
  echo "Graphics bundle for Windows 11 not found. Falling back to a standard Windows 11 bundle..."
  BUNDLE_ID=$(aws workspaces describe-workspace-bundles \
    --owner AMAZON \
    --query "Bundles[?contains(Name, 'Windows 11')] | [0].BundleId" \
    --output text)
fi

if [ -z "$BUNDLE_ID" ] || [ "$BUNDLE_ID" == "None" ]; then
  echo "No Windows 11 bundle found. Falling back to Windows 10 bundle..."
  BUNDLE_ID=$(aws workspaces describe-workspace-bundles \
    --owner AMAZON \
    --query "Bundles[?contains(Name, 'Windows 10')] | [0].BundleId" \
    --output text)
fi

echo "Using bundle ID: $BUNDLE_ID"

# Save the bundle ID to the resources file
echo "BUNDLE_ID=$BUNDLE_ID" >> workspace-resources.txt

echo "WorkSpaces setup completed successfully!" 