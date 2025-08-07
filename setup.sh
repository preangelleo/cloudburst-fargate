#!/bin/bash

# CloudBurst Fargate - Smart Setup Script
# Automatically configures AWS resources and generates .env file
# Usage: ./setup.sh

set -e

echo "🚀 CloudBurst Fargate - Smart Setup"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="cloudburst-cluster"
TASK_FAMILY="cloudburst-task"
SERVICE_ROLE_NAME="ecsTaskExecutionRole"
LOG_GROUP_NAME="/ecs/cloudburst"
REGION="us-east-1"
DOCKER_IMAGE="betashow/video-generation-api:latest"

# Function to print colored output
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 0: Check prerequisites
print_step "Step 0: Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first:"
    echo "  • macOS: brew install awscli"
    echo "  • Linux: sudo apt-get install awscli"
    echo "  • Windows: Download from AWS website"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid"
    echo ""
    echo "Please configure AWS CLI with your Access Keys:"
    echo "  aws configure"
    echo ""
    echo "You'll need:"
    echo "  • AWS Access Key ID"
    echo "  • AWS Secret Access Key"
    echo "  • Default region (recommend: us-east-1)"
    echo "  • Default output format (recommend: json)"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CALLER_IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)

print_success "AWS CLI configured"
echo "  • Account ID: $ACCOUNT_ID"
echo "  • Identity: $CALLER_IDENTITY"
echo ""

# Step 1: Auto-discover network resources
print_step "Step 1: Auto-discovering network resources..."

# Find default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$DEFAULT_VPC" = "None" ] || [ "$DEFAULT_VPC" = "null" ]; then
    print_warning "No default VPC found, looking for any VPC..."
    DEFAULT_VPC=$(aws ec2 describe-vpcs \
        --query 'Vpcs[0].VpcId' \
        --output text \
        --region "$REGION" 2>/dev/null || echo "None")
fi

if [ "$DEFAULT_VPC" = "None" ] || [ "$DEFAULT_VPC" = "null" ]; then
    print_error "No VPC found in region $REGION"
    echo "Please create a VPC first or choose a different region"
    exit 1
fi

print_success "Found VPC: $DEFAULT_VPC"

# Find public subnet in the VPC
PUBLIC_SUBNET=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" "Name=map-public-ip-on-launch,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$PUBLIC_SUBNET" = "None" ] || [ "$PUBLIC_SUBNET" = "null" ]; then
    print_warning "No public subnet found, using first available subnet..."
    PUBLIC_SUBNET=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$DEFAULT_VPC" \
        --query 'Subnets[0].SubnetId' \
        --output text \
        --region "$REGION" 2>/dev/null || echo "None")
fi

if [ "$PUBLIC_SUBNET" = "None" ] || [ "$PUBLIC_SUBNET" = "null" ]; then
    print_error "No subnet found in VPC $DEFAULT_VPC"
    exit 1
fi

print_success "Found subnet: $PUBLIC_SUBNET"

# Find or create security group
SG_NAME="cloudburst-fargate-sg"
SECURITY_GROUP=$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" "Name=group-name,Values=$SG_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$SECURITY_GROUP" = "None" ] || [ "$SECURITY_GROUP" = "null" ]; then
    print_step "Creating security group for CloudBurst Fargate..."
    
    SECURITY_GROUP=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "CloudBurst Fargate Security Group - Auto-created" \
        --vpc-id "$DEFAULT_VPC" \
        --query 'GroupId' \
        --output text \
        --region "$REGION")
    
    # Add inbound rule for port 5000 (API access)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP" \
        --protocol tcp \
        --port 5000 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" > /dev/null 2>&1 || true
    
    # Add outbound rule for HTTPS (Docker pulls)
    aws ec2 authorize-security-group-egress \
        --group-id "$SECURITY_GROUP" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" > /dev/null 2>&1 || true
    
    # Add outbound rule for HTTP (backup)
    aws ec2 authorize-security-group-egress \
        --group-id "$SECURITY_GROUP" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" > /dev/null 2>&1 || true
    
    print_success "Created security group: $SECURITY_GROUP"
else
    print_success "Found existing security group: $SECURITY_GROUP"
fi

echo ""

# Step 2: Create AWS infrastructure
print_step "Step 2: Creating AWS ECS infrastructure..."

# Create ECS Cluster
if aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$REGION" > /dev/null 2>&1; then
    print_success "ECS cluster '$CLUSTER_NAME' already exists"
else
    aws ecs create-cluster --cluster-name "$CLUSTER_NAME" --region "$REGION" > /dev/null
    print_success "Created ECS cluster: $CLUSTER_NAME"
fi

# Create CloudWatch Log Group
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$REGION" 2>/dev/null | grep -q "$LOG_GROUP_NAME"; then
    print_success "CloudWatch log group '$LOG_GROUP_NAME' already exists"
else
    aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" --region "$REGION"
    print_success "Created CloudWatch log group: $LOG_GROUP_NAME"
fi

# Create IAM execution role
if aws iam get-role --role-name "$SERVICE_ROLE_NAME" > /dev/null 2>&1; then
    print_success "IAM role '$SERVICE_ROLE_NAME' already exists"
else
    # Create trust policy
    cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
        --role-name "$SERVICE_ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json > /dev/null
    
    aws iam attach-role-policy \
        --role-name "$SERVICE_ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" > /dev/null
    
    print_success "Created IAM execution role: $SERVICE_ROLE_NAME"
    rm /tmp/trust-policy.json
fi

# Register Task Definition
print_step "Registering ECS task definition..."

cat > /tmp/task-definition.json << EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/$SERVICE_ROLE_NAME",
  "containerDefinitions": [
    {
      "name": "cloudburst-processor",
      "image": "$DOCKER_IMAGE",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "$REGION"
        },
        {
          "name": "ENVIRONMENT",
          "value": "fargate"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "$LOG_GROUP_NAME",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:5000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-definition.json \
    --region "$REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

print_success "Registered task definition: $TASK_FAMILY:1"
rm /tmp/task-definition.json

echo ""

# Step 3: Generate .env file
print_step "Step 3: Generating .env configuration file..."

# Get current AWS credentials
AWS_ACCESS_KEY=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
AWS_SECRET_KEY=$(aws configure get aws_secret_access_key 2>/dev/null || echo "")

if [ -z "$AWS_ACCESS_KEY" ] || [ -z "$AWS_SECRET_KEY" ]; then
    print_warning "Could not retrieve AWS credentials from AWS CLI config"
    print_warning "You may need to manually add AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to .env"
fi

# Create .env file
cat > .env << EOF
# Fargate Operation v1.0 - Environment Configuration
# Auto-generated by setup.sh on $(date)

# =============================================================================
# ✅ AUTO-CONFIGURED: Generated by setup script
# =============================================================================

# AWS Credentials
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY
AWS_REGION=$REGION

# Auto-discovered network configuration
AWS_SUBNET_ID=$PUBLIC_SUBNET
AWS_SECURITY_GROUP_ID=$SECURITY_GROUP

# ECS Fargate Resources (auto-created)
ECS_CLUSTER_NAME=$CLUSTER_NAME
ECS_TASK_DEFINITION=$TASK_FAMILY:1
DOCKER_IMAGE=$DOCKER_IMAGE

# =============================================================================
# ⚙️ STANDARD CONFIGURATION: Usually don't need to change
# =============================================================================

# API Configuration
API_TIMEOUT_MINUTES=15
API_REQUEST_TIMEOUT_SECONDS=300

# Results Storage
RESULTS_DIR=/tmp/cloudburst_fargate_results

# Optional: S3 bucket for file storage/transfer
# S3_BUCKET=your-cloudburst-bucket
# S3_REGION=$REGION

# IAM Role Session (for advanced usage)
AWS_ROLE_SESSION_NAME=cloudburst-fargate-session

# Task Resource Configuration (overridden by priority settings)
# Priority 1: 2048 CPU (2 vCPU), 4096 Memory (4GB) - Standard
# Priority 2: 4096 CPU (4 vCPU), 8192 Memory (8GB) - High Performance  
# Priority 3: 1024 CPU (1 vCPU), 2048 Memory (2GB) - Economy
EOF

print_success "Generated .env file with auto-discovered configuration"
echo ""

# Step 4: Final summary and next steps
echo ""
echo -e "${GREEN}🎉 CloudBurst Fargate Setup Complete!${NC}"
echo "============================================="
echo ""
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "  • AWS Account: $ACCOUNT_ID"
echo "  • Region: $REGION"
echo "  • VPC: $DEFAULT_VPC"
echo "  • Subnet: $PUBLIC_SUBNET (auto-discovered)"
echo "  • Security Group: $SECURITY_GROUP (auto-configured)"
echo "  • ECS Cluster: $CLUSTER_NAME"
echo "  • Task Definition: $TASK_FAMILY:1"
echo "  • Docker Image: $DOCKER_IMAGE"
echo ""
echo -e "${BLUE}✅ Ready to use!${NC}"
echo ""
echo -e "${YELLOW}🚀 Quick Start:${NC}"
echo "  # Test single scene processing"
echo "  python3 -c \"from fargate_operation_v1 import FargateOperationV1; print('✅ Ready!')\" "
echo ""
echo "  # Or run a complete example"
echo "  python3 example_usage.py"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "  • See example_usage.py for complete API examples"
echo "  • See README.md for detailed usage instructions"
echo "  • See .env file for all configuration options"
echo ""
echo -e "${GREEN}✨ Everything is configured automatically!${NC}"
echo "   Your AWS resources are ready and .env file is generated."
echo "   You can start processing videos immediately!"
echo ""