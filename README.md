# AWS WorkSpaces with Windows 11 for Revit

This project automates the setup of AWS WorkSpaces with Windows 11 for running Revit via CLI.

## Prerequisites

1. AWS CLI installed and configured
2. AWS account with appropriate permissions
3. AWS credentials configured

## Quick Start

Run the main setup script to create all resources:

```bash
chmod +x setup-workspaces.sh
./setup-workspaces.sh
```

This will perform the following steps:
1. Create a VPC with public and private subnets
2. Set up a Simple AD directory
3. Register the directory with WorkSpaces
4. Create a Windows 11 WorkSpace with graphics capabilities

## Step-by-Step Setup

You can also run each script individually if needed:

1. **VPC Setup**:
   ```bash
   ./vpc-setup.sh
   ```
   Creates a VPC with public and private subnets, internet gateway, and route tables.

2. **Directory Setup**:
   ```bash
   ./directory-setup.sh
   ```
   Creates a Simple AD directory for user management.

3. **WorkSpaces Setup**:
   ```bash
   ./workspaces-setup.sh
   ```
   Registers the directory with WorkSpaces and identifies a suitable Windows 11 bundle.

4. **WorkSpace Creation**:
   ```bash
   ./create-workspace.sh
   ```
   Creates a Windows 11 WorkSpace with graphics capabilities for running Revit.

## Cleanup

To avoid ongoing charges, you can clean up all resources when no longer needed:

```bash
chmod +x cleanup-workspaces.sh
./cleanup-workspaces.sh
```

This will:
1. Terminate WorkSpaces
2. Deregister directories from WorkSpaces
3. Delete directories
4. Delete VPC resources

## Resource Tracking

All created resources are tracked in the `workspace-resources.txt` file, which is generated during the setup process.