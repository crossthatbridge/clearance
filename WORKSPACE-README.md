# AWS WorkSpaces Windows 11 Setup

This repository contains scripts to set up AWS WorkSpaces with Windows 11 for Revit usage via CLI.

## Prerequisites

1. AWS CLI installed and configured
2. AWS account with appropriate permissions
3. AWS credentials in your `.envrc` file

## Setup Process

The setup process is divided into four main steps:

1. **VPC Setup**: Creates a VPC with public and private subnets, internet gateway, and route tables
2. **Directory Setup**: Creates a Simple AD directory for user management
3. **WorkSpaces Setup**: Registers the directory with WorkSpaces and finds an appropriate Windows 11 bundle
4. **WorkSpace Creation**: Creates a Windows 11 WorkSpace for a user

## How to Run

Run the main setup script:

```bash
chmod +x setup-workspaces.sh
./setup-workspaces.sh
```

This script will execute all the steps in sequence.

## Individual Scripts

You can also run each script individually if needed:

- `vpc-setup.sh`: Sets up the VPC infrastructure
- `directory-setup.sh`: Sets up the Simple AD directory
- `workspaces-setup.sh`: Sets up WorkSpaces configuration
- `create-workspace.sh`: Creates the actual WorkSpace

## Resource Tracking

All created resources are tracked in the `workspace-resources.txt` file, which is generated during the setup process.

## Connecting to Your WorkSpace

After the setup is complete, you can connect to your WorkSpace using the Amazon WorkSpaces client. The connection information will be displayed at the end of the setup process.

## Cleanup

To avoid ongoing charges, you should clean up resources when they are no longer needed. Use the cleanup script:

```bash
chmod +x cleanup-workspaces.sh
./cleanup-workspaces.sh
```

This script will:

1. Terminate WorkSpaces
2. Deregister directories from WorkSpaces
3. Delete directories
4. Delete VPC resources (subnets, internet gateway, route tables, VPC)

The script uses the resource IDs stored in `workspace-resources.txt` to ensure all created resources are properly cleaned up. 