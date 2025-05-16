#!/bin/bash
set -e

# Load environment variables from .envrc file
[ -f .envrc ] && source .envrc
export AWS_DEFAULT_REGION=eu-west-1

# Load resources
source workspace-resources.txt

# User configuration from .envrc
# Check if variables are set in environment, otherwise use defaults
USERNAME=${USERNAME:-"Administrator"}
PASSWORD=${PASSWORD:-"PLEASE_SET_PASSWORD_IN_ENVRC"}

# Check if DIRECTORY_ID is set
if [ -z "$DIRECTORY_ID" ]; then
  echo "Creating a new directory..."
  DIRECTORY_RESPONSE=$(aws ds create-directory \
    --name "clearance.local" \
    --password $PASSWORD \
    --size Small \
    --vpc-settings "VpcId=$VPC_ID,SubnetIds=[$PUBLIC_SUBNET_ID,$PRIVATE_SUBNET_ID]" \
    --output json)

  DIRECTORY_ID=$(echo $DIRECTORY_RESPONSE | jq -r '.DirectoryId')
  echo "New Directory created with ID: $DIRECTORY_ID"
  echo "DIRECTORY_ID=$DIRECTORY_ID" >> workspace-resources.txt

  echo "Waiting for directory to become active..."
  DIR_STATUS="CREATING"
  while [ "$DIR_STATUS" != "ACTIVE" ]; do
    DIR_STATUS=$(aws ds describe-directories \
      --directory-ids $DIRECTORY_ID \
      --query "DirectoryDescriptions[0].Stage" \
      --output text)
    echo "Directory status: $DIR_STATUS"
    if [ "$DIR_STATUS" == "ACTIVE" ]; then
      break
    elif [ "$DIR_STATUS" == "FAILED" ]; then
      echo "Directory creation failed. Please check the AWS console."
      exit 1
    fi
    echo "Waiting for directory to become active..."
    sleep 30
  done
  echo "Directory is now active!"
fi

# Create a user in the directory
echo "Creating user in the directory..."
aws ds create-user \
  --directory-id $DIRECTORY_ID \
  --username $USERNAME \
  --password $PASSWORD \
  --given-name "Admin" \
  --surname "User" \
  --display-name "Administrator" || {
    echo "User may already exist, continuing..."
  }

echo "User created or already exists!"

# Check if BUNDLE_ID is set
if [ -z "$BUNDLE_ID" ]; then
  echo "No bundle ID specified, finding a suitable Windows bundle..."
  BUNDLE_RESPONSE=$(aws workspaces describe-workspace-bundles \
    --owner AMAZON \
    --output json)

  # First try to find a Windows 11 Graphics bundle
  BUNDLE_ID=$(echo $BUNDLE_RESPONSE | jq -r '.Bundles[] | select(.Name | contains("Windows 11") and contains("Graphics")) | .BundleId' | head -1)

  # If no Windows 11 Graphics bundle is found, try any Windows Graphics bundle
  if [ -z "$BUNDLE_ID" ]; then
    BUNDLE_ID=$(echo $BUNDLE_RESPONSE | jq -r '.Bundles[] | select(.Name | contains("Windows") and contains("Graphics")) | .BundleId' | head -1)
  fi

  # If still no Graphics bundle, try any Windows bundle
  if [ -z "$BUNDLE_ID" ]; then
    BUNDLE_ID=$(echo $BUNDLE_RESPONSE | jq -r '.Bundles[] | select(.Name | contains("Windows")) | .BundleId' | head -1)
  fi

  # If still nothing, use any bundle
  if [ -z "$BUNDLE_ID" ]; then
    BUNDLE_ID=$(echo $BUNDLE_RESPONSE | jq -r '.Bundles[0].BundleId')
  fi

  if [ -z "$BUNDLE_ID" ]; then
    echo "Could not find any suitable WorkSpace bundle. Please specify a bundle ID manually."
    exit 1
  fi

  echo "Selected bundle ID: $BUNDLE_ID"
  echo "BUNDLE_ID=$BUNDLE_ID" >> workspace-resources.txt
fi

# Create the WorkSpace
echo "Creating WorkSpace for user $USERNAME..."
WORKSPACE_RESPONSE=$(aws workspaces create-workspaces \
  --workspaces "[{\"DirectoryId\":\"$DIRECTORY_ID\",\"UserName\":\"$USERNAME\",\"BundleId\":\"$BUNDLE_ID\",\"WorkspaceProperties\":{\"RunningMode\":\"ALWAYS_ON\",\"RootVolumeSizeGib\":80,\"UserVolumeSizeGib\":50,\"ComputeTypeName\":\"STANDARD\",\"Protocols\":[\"PCOIP\"]},\"Tags\":[{\"Key\":\"Project\",\"Value\":\"Clearance\"},{\"Key\":\"Application\",\"Value\":\"Revit\"}]}]" \
  --output json)

# Check if there are failed requests
FAILED_REQUESTS=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests | length')

if [ "$FAILED_REQUESTS" -gt 0 ]; then
  ERROR_CODE=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests[0].ErrorCode')
  ERROR_MESSAGE=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests[0].ErrorMessage')

  if [ "$ERROR_CODE" == "ResourceAlreadyExistsException" ]; then
    echo "WorkSpace already exists for this user. Getting existing WorkSpace ID..."
  elif [ "$ERROR_CODE" == "ResourceLimitExceededException" ]; then
    echo "Resource limit exceeded. Checking if you can use existing resources..."
    # Continue with existing workspaces
  elif [ "$ERROR_CODE" == "InvalidParameterValuesException" ] && [[ "$ERROR_MESSAGE" == *"specified ResourceNotFoundException"* ]]; then
    echo "Directory may not be fully available yet. Waiting 60 more seconds..."
    sleep 60
    echo "Retrying WorkSpace creation..."
    WORKSPACE_RESPONSE=$(aws workspaces create-workspaces \
      --workspaces "[{\"DirectoryId\":\"$DIRECTORY_ID\",\"UserName\":\"$USERNAME\",\"BundleId\":\"$BUNDLE_ID\",\"WorkspaceProperties\":{\"RunningMode\":\"ALWAYS_ON\",\"RootVolumeSizeGib\":80,\"UserVolumeSizeGib\":50,\"ComputeTypeName\":\"STANDARD\",\"Protocols\":[\"PCOIP\"]},\"Tags\":[{\"Key\":\"Project\",\"Value\":\"Clearance\"},{\"Key\":\"Application\",\"Value\":\"Revit\"}]}]" \
      --output json)
    # Check again after retry
    FAILED_REQUESTS=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests | length')
    if [ "$FAILED_REQUESTS" -gt 0 ]; then
      ERROR_CODE=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests[0].ErrorCode')
      ERROR_MESSAGE=$(echo $WORKSPACE_RESPONSE | jq -r '.FailedRequests[0].ErrorMessage')
      if [ "$ERROR_CODE" == "ResourceAlreadyExistsException" ]; then
        echo "WorkSpace already exists for this user. Getting existing WorkSpace ID..."
      else
        echo "Failed to create WorkSpace after retry: $ERROR_CODE - $ERROR_MESSAGE"
        echo "Checking if workspace already exists despite the error..."
      fi
    fi
  else
    echo "Failed to create WorkSpace: $ERROR_CODE - $ERROR_MESSAGE"
    echo "Checking if workspace already exists despite the error..."
  fi
fi

# Get the WorkSpace ID
WORKSPACE_ID=$(aws workspaces describe-workspaces \
  --directory-id $DIRECTORY_ID \
  --user-name $USERNAME \
  --query "Workspaces[0].WorkspaceId" \
  --output text)

if [ -z "$WORKSPACE_ID" ] || [ "$WORKSPACE_ID" == "None" ]; then
  echo "Failed to get WorkSpace ID. Please check the AWS console for more details."
  exit 1
fi
  
echo "WorkSpace ID: $WORKSPACE_ID"

# Save the workspace ID to the resources file
echo "WORKSPACE_ID=$WORKSPACE_ID" >> workspace-resources.txt

echo "Waiting for WorkSpace to be available (this may take 20-30 minutes)..."

# Set a timeout for workspace creation (2 hours = 120 minutes = 7200 seconds)
TIMEOUT=7200
START_TIME=$(date +%s)

# Poll for workspace status
WORKSPACE_STATE="PENDING"
while [ "$WORKSPACE_STATE" != "AVAILABLE" ]; do
  WORKSPACE_STATE=$(aws workspaces describe-workspaces \
    --workspace-ids $WORKSPACE_ID \
    --query "Workspaces[0].State" \
    --output text)

  # Check the current time
  CURRENT_TIME=$(date +%s)
  ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
  MINUTES_ELAPSED=$((ELAPSED_TIME / 60))

  echo "WorkSpace state: $WORKSPACE_STATE (elapsed time: $MINUTES_ELAPSED minutes)"

  if [ "$WORKSPACE_STATE" == "AVAILABLE" ]; then
    break
  elif [ "$WORKSPACE_STATE" == "ERROR" ]; then
    echo "Error creating WorkSpace. Please check the AWS console for more details."
    exit 1
  fi

  # Check if we've exceeded the timeout
  if [ $ELAPSED_TIME -gt $TIMEOUT ]; then
    echo "Timed out waiting for WorkSpace to become available (after $MINUTES_ELAPSED minutes)."
    echo "The WorkSpace may still be creating. You can check its status later with:"
    echo "aws workspaces describe-workspaces --workspace-ids $WORKSPACE_ID"
    exit 1
  fi

  # Display a progress message with time remaining estimate
  TIME_REMAINING=$((30 - MINUTES_ELAPSED))
  if [ $TIME_REMAINING -lt 0 ]; then
    TIME_REMAINING=0
  fi
  echo "Waiting for WorkSpace to be available... (estimated time remaining: ~$TIME_REMAINING minutes)"

  # Sleep for 60 seconds before checking again
  sleep 60
done

echo "WorkSpace is now available!"

# Get connection information
echo "Getting connection information..."
CONNECTION_INFO=$(aws workspaces describe-workspaces \
  --workspace-ids $WORKSPACE_ID \
  --query "Workspaces[0].{State:State,IPAddress:IpAddress,ComputerName:ComputerName}" \
  --output json)

echo "Connection Information:"
echo "$CONNECTION_INFO"

echo "WorkSpace creation completed successfully!"
echo "You can now connect to your Windows 11 WorkSpace using the Amazon WorkSpaces client." 