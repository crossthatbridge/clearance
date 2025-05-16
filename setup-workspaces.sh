#!/bin/bash
set -e

# Make all scripts executable
chmod +x vpc-setup.sh
chmod +x directory-setup.sh
chmod +x workspaces-setup.sh
chmod +x create-workspace.sh

echo "==============================================="
echo "AWS WorkSpaces with Windows 11 Setup"
echo "==============================================="

echo "Step 1: Setting up VPC..."
./vpc-setup.sh
echo "VPC setup completed!"

echo "Step 2: Setting up Directory..."
./directory-setup.sh
echo "Directory setup completed!"

echo "Step 3: Setting up WorkSpaces..."
./workspaces-setup.sh
echo "WorkSpaces setup completed!"

echo "Step 4: Creating WorkSpace..."
./create-workspace.sh
echo "WorkSpace creation completed!"

echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo "Your Windows 11 WorkSpace has been created."
echo "You can connect to it using the Amazon WorkSpaces client."
echo "Check workspace-resources.txt for all resource IDs." 