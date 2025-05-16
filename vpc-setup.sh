#!/bin/bash
set -e

# Load environment variables from .envrc file
[ -f .envrc ] && source .envrc
export AWS_DEFAULT_REGION=us-east-1

echo "Creating VPC for WorkSpaces..."
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=workspaces-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)

echo "VPC created: $VPC_ID"

# Enable DNS support and hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create public subnet in AZ a
echo "Creating public subnet in AZ a..."
PUBLIC_SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${AWS_DEFAULT_REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=workspaces-public-subnet}]' \
  --query 'Subnet.SubnetId' \
  --output text)

echo "Public subnet created: $PUBLIC_SUBNET_ID"

# Create private subnet in AZ b
echo "Creating private subnet in AZ b..."
PRIVATE_SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ${AWS_DEFAULT_REGION}b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=workspaces-private-subnet}]' \
  --query 'Subnet.SubnetId' \
  --output text)

echo "Private subnet created: $PRIVATE_SUBNET_ID"

# Create Internet Gateway
echo "Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=workspaces-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)

echo "Internet Gateway created: $IGW_ID"

# Attach Internet Gateway to VPC
echo "Attaching Internet Gateway to VPC..."
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID

# Create public route table
echo "Creating public route table..."
PUBLIC_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=workspaces-public-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

echo "Public route table created: $PUBLIC_RT_ID"

# Create route to Internet Gateway
echo "Adding route to Internet Gateway..."
aws ec2 create-route --route-table-id $PUBLIC_RT_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID

# Associate public subnet with public route table
echo "Associating public subnet with public route table..."
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_ID

# Create private route table
echo "Creating private route table..."
PRIVATE_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=workspaces-private-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

echo "Private route table created: $PRIVATE_RT_ID"

# Associate private subnet with private route table
echo "Associating private subnet with private route table..."
aws ec2 associate-route-table --route-table-id $PRIVATE_RT_ID --subnet-id $PRIVATE_SUBNET_ID

# Save the IDs to a file for later use
echo "Saving resource IDs to workspace-resources.txt..."
cat > workspace-resources.txt << EOF
VPC_ID=$VPC_ID
PUBLIC_SUBNET_ID=$PUBLIC_SUBNET_ID
PRIVATE_SUBNET_ID=$PRIVATE_SUBNET_ID
IGW_ID=$IGW_ID
PUBLIC_RT_ID=$PUBLIC_RT_ID
PRIVATE_RT_ID=$PRIVATE_RT_ID
EOF

echo "VPC setup completed successfully!" 