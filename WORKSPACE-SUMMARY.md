# AWS WorkSpaces Windows 11 Setup Summary

## Overview

This project provides a complete CLI-based solution for setting up Amazon WorkSpaces with Windows 11, specifically configured for Revit usage. The setup is automated through a series of bash scripts that handle everything from VPC creation to WorkSpace deployment.

## Components Created

1. **VPC Infrastructure**
   - VPC with CIDR block 10.0.0.0/16
   - Public subnet (10.0.1.0/24)
   - Private subnet (10.0.2.0/24)
   - Internet Gateway
   - Route tables for public and private subnets

2. **Directory Service**
   - Simple AD directory (clearance.local)
   - Administrator user account

3. **WorkSpaces Configuration**
   - Directory registered with WorkSpaces service
   - Graphics bundle for Windows 11 (suitable for Revit)

4. **WorkSpace Instance**
   - Windows 11 WorkSpace with graphics capabilities
   - 100GB root volume
   - 100GB user volume
   - Always-on running mode

## Usage Instructions

### Setting Up WorkSpaces

1. Run the main setup script:
   ```bash
   ./setup-workspaces.sh
   ```

2. Wait for the setup process to complete (approximately 30-45 minutes total)

3. Connect to your WorkSpace using the Amazon WorkSpaces client

### Cleaning Up Resources

When you no longer need the WorkSpaces environment:

1. Run the cleanup script:
   ```bash
   ./cleanup-workspaces.sh
   ```

2. Wait for all resources to be deleted

## Resource Management

All created AWS resources are tracked in the `workspace-resources.txt` file, which is automatically generated during setup. This file is used by the cleanup script to ensure all resources are properly deleted.

## Security Considerations

- Credentials are stored in environment variables
- The VPC is configured with public and private subnets for security
- The WorkSpace is accessible only to authorized users

## Cost Considerations

Running WorkSpaces incurs costs based on:
- WorkSpace bundle type (Graphics)
- Running mode (Always-on)
- Storage volumes (100GB root + 100GB user)
- Directory service (Simple AD)

Make sure to clean up resources when not in use to avoid unnecessary charges. 