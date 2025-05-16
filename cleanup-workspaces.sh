#!/bin/bash
set -e

# Load environment variables from .envrc file
[ -f .envrc ] && source .envrc
export AWS_DEFAULT_REGION=us-east-1

# Check if resources file exists
if [ ! -f workspace-resources.txt ]; then
  echo "Error: workspace-resources.txt not found. Cannot clean up resources."
  exit 1
fi

# Load resources
source workspace-resources.txt

echo "==============================================="
echo "AWS WorkSpaces Cleanup"
echo "==============================================="

# Step 1: Terminate WorkSpace
if [ ! -z "$WORKSPACE_ID" ]; then
  echo "Terminating WorkSpace: $WORKSPACE_ID..."
  aws workspaces terminate-workspaces --terminate-workspace-requests WorkspaceId=$WORKSPACE_ID
  echo "Waiting for WorkSpace to be terminated..."
  sleep 60
  echo "WorkSpace terminated."
else
  echo "No WorkSpace ID found, skipping WorkSpace termination."
fi

# Step 2: Deregister directory from WorkSpaces
if [ ! -z "$DIRECTORY_ID" ]; then
  echo "Deregistering directory from WorkSpaces: $DIRECTORY_ID..."
  aws workspaces deregister-directory --directory-id $DIRECTORY_ID
  echo "Waiting for directory to be deregistered..."
  sleep 60
  echo "Directory deregistered from WorkSpaces."
else
  echo "No Directory ID found, skipping directory deregistration."
fi

# Step 3: Delete directory
if [ ! -z "$DIRECTORY_ID" ]; then
  echo "Deleting directory: $DIRECTORY_ID..."
  aws ds delete-directory --directory-id $DIRECTORY_ID
  echo "Waiting for directory to be deleted..."
  sleep 180
  echo "Directory deleted."
else
  echo "No Directory ID found, skipping directory deletion."
fi

# Step 4: Delete VPC resources
if [ ! -z "$VPC_ID" ]; then
  # Delete route tables
  if [ ! -z "$PUBLIC_RT_ID" ]; then
    echo "Disassociating and deleting public route table: $PUBLIC_RT_ID..."
    ASSOCIATIONS=$(aws ec2 describe-route-tables --route-table-ids $PUBLIC_RT_ID --query 'RouteTables[0].Associations[*].RouteTableAssociationId' --output text)
    for ASSOC in $ASSOCIATIONS; do
      aws ec2 disassociate-route-table --association-id $ASSOC
    done
    aws ec2 delete-route-table --route-table-id $PUBLIC_RT_ID
    echo "Public route table deleted."
  fi
  
  if [ ! -z "$PRIVATE_RT_ID" ]; then
    echo "Disassociating and deleting private route table: $PRIVATE_RT_ID..."
    ASSOCIATIONS=$(aws ec2 describe-route-tables --route-table-ids $PRIVATE_RT_ID --query 'RouteTables[0].Associations[*].RouteTableAssociationId' --output text)
    for ASSOC in $ASSOCIATIONS; do
      aws ec2 disassociate-route-table --association-id $ASSOC
    done
    aws ec2 delete-route-table --route-table-id $PRIVATE_RT_ID
    echo "Private route table deleted."
  fi
  
  # Detach and delete internet gateway
  if [ ! -z "$IGW_ID" ]; then
    echo "Detaching and deleting internet gateway: $IGW_ID..."
    aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
    aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID
    echo "Internet gateway deleted."
  fi
  
  # Delete subnets
  if [ ! -z "$PUBLIC_SUBNET_ID" ]; then
    echo "Deleting public subnet: $PUBLIC_SUBNET_ID..."
    aws ec2 delete-subnet --subnet-id $PUBLIC_SUBNET_ID
    echo "Public subnet deleted."
  fi
  
  if [ ! -z "$PRIVATE_SUBNET_ID" ]; then
    echo "Deleting private subnet: $PRIVATE_SUBNET_ID..."
    aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_ID
    echo "Private subnet deleted."
  fi
  
  # Delete VPC
  echo "Deleting VPC: $VPC_ID..."
  aws ec2 delete-vpc --vpc-id $VPC_ID
  echo "VPC deleted."
else
  echo "No VPC ID found, skipping VPC resource deletion."
fi

echo "Removing workspace-resources.txt..."
rm -f workspace-resources.txt

echo "==============================================="
echo "Cleanup Complete!"
echo "==============================================="
echo "All AWS WorkSpaces resources have been deleted." 