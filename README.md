# CloudBurst Fargate - Serverless Video Processing

My second open source project, now powered by **AWS ECS Fargate**! 🚀

> **📚 Related Projects**: 
> - **Original CloudBurst (EC2)**: https://github.com/preangelleo/sumatman/tree/main/runpod/cloudburst
> - **Video Generation API**: https://github.com/preangelleo/video-generation-docker
> - **中文文档**: [README_CN.md](./README_CN.md)

## What is this?

A production-ready Python framework that uses **AWS ECS Fargate** for serverless, on-demand video generation with **parallel processing capabilities**.

**Core Value**: When your application needs to generate videos (using our [Video Generation API](https://github.com/preangelleo/video-generation-docker)), this framework:
- 🚀 Starts Fargate containers in **30 seconds** (vs 2+ minutes for EC2)
- ⚡ **Parallel processing**: Handle multiple scenes across concurrent containers
- 🎬 Processes your video generation requests with zero infrastructure management
- 📥 Downloads completed videos automatically with "process one → download one" efficiency
- 🛑 Containers terminate automatically after processing
- 💰 Pay-per-second billing with **no idle costs**

**Perfect for**: Production applications that need scalable serverless video processing without the complexity of managing EC2 instances.

## 🆚 CloudBurst Evolution: EC2 → Fargate

| Feature | CloudBurst EC2 (v1) | **CloudBurst Fargate (v2)** |
|---------|---------------------|------------------------------|
| **Startup Time** | ~75 seconds | **~30 seconds** ⚡ |
| **Infrastructure** | Manage EC2 instances | **Fully serverless** 🎯 |
| **Parallel Processing** | Single instance only | **Multiple concurrent tasks** 🔄 |
| **Availability** | Subject to quota limits | **Near 100% availability** ✅ |
| **Scaling** | Limited by EC2 capacity | **Unlimited concurrent tasks** 📈 |
| **Cost Model** | Per-minute billing | **Per-second billing** 💰 |
| **Idle Costs** | Risk of forgotten instances | **Zero idle costs** 🔥 |

## 🚀 Quick Start

### 1. Install Dependencies
```bash
git clone https://github.com/preangelleo/cloudburst
cd cloudburst_fargate
pip install -r requirements.txt
```

### 2. Setup AWS Permissions (CRITICAL)

CloudBurst Fargate requires specific IAM permissions to manage ECS tasks, access VPC resources, and handle container operations. You'll need to add permissions **4 times** during setup:

#### Required IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:StopTask", 
        "ecs:DescribeTasks",
        "ecs:DescribeClusters",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:DescribeVpcs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/ecs/cloudburst*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/ecsTaskExecutionRole"
    }
  ]
}
```

#### Step-by-Step Permission Setup
1. **First Permission**: ECS Task Management
   ```bash
   # Add ECS permissions for running and managing Fargate tasks
   aws iam attach-user-policy --user-name YOUR_USER --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
   ```

2. **Second Permission**: VPC and Network Access  
   ```bash
   # Add EC2 permissions for VPC, subnets, and security groups
   aws iam attach-user-policy --user-name YOUR_USER --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess
   ```

3. **Third Permission**: CloudWatch Logs
   ```bash
   # Add CloudWatch permissions for container logging
   aws iam attach-user-policy --user-name YOUR_USER --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
   ```

4. **Fourth Permission**: IAM Role Passing
   ```bash
   # Add permission to pass execution roles to ECS tasks
   aws iam put-user-policy --user-name YOUR_USER --policy-name ECSTaskRolePass --policy-document file://pass-role-policy.json
   ```

### 3. Setup Environment
```bash
# Copy and customize configuration
cp .env.example .env

# Edit .env with your AWS credentials and VPC settings:
# - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (with permissions above)
# - AWS_SUBNET_ID (your VPC subnet with internet access) 
# - AWS_SECURITY_GROUP_ID (allows port 5000 and outbound HTTPS)
```

### 4. Test Your Setup
```python
from fargate_operation_v1 import FargateOperationV1

# Quick single-scene test
processor = FargateOperationV1(config_priority=1)
scenes = [{
    "scene_name": "test_scene",
    "image_path": "path/to/image.png",
    "audio_path": "path/to/audio.mp3",
    "subtitle_path": "path/to/subtitle.srt"  # Optional
}]

result = processor.execute_batch(scenes, language="english", enable_zoom=True)
print(f"✅ Generated {result['successful_scenes']} videos")
```

### 5. Parallel Processing (Production Ready!)
```python
from fargate_operation_v1 import execute_parallel_batches

# Process multiple scenes across parallel Fargate containers
scenes = [
    {"scene_name": "scene_001", "image_path": "...", "audio_path": "..."},
    {"scene_name": "scene_002", "image_path": "...", "audio_path": "..."},
    {"scene_name": "scene_003", "image_path": "...", "audio_path": "..."},
    {"scene_name": "scene_004", "image_path": "...", "audio_path": "..."}
]

# Automatically distribute across 2 parallel tasks (2 scenes each)
result = execute_parallel_batches(
    scenes=scenes,
    scenes_per_batch=2,        # 2 scenes per Fargate container
    max_parallel_tasks=2,      # 2 concurrent containers
    language="english",
    enable_zoom=True,
    saving_dir="./output"
)

print(f"🚀 Efficiency: {result['efficiency']['speedup_factor']:.2f}x speedup")
print(f"💰 Total cost: ${result['total_cost_usd']:.4f}")
print(f"📁 {len(result['downloaded_files'])} videos downloaded")
```

## ⚡ Parallel Processing Architecture

CloudBurst Fargate v2 introduces **true parallel processing**:

### Architecture Benefits
- **Concurrent Tasks**: Multiple Fargate containers running simultaneously
- **Intelligent Distribution**: Scenes automatically distributed across tasks
- **Efficient Workflow**: Each task processes scenes → downloads → terminates
- **Cost Optimized**: Pay only for actual processing time across all containers

### Example: 4 Scenes, 2 Tasks
```
Task 1: Start → Process scene_001 → Download → Process scene_002 → Download → Terminate
Task 2: Start → Process scene_003 → Download → Process scene_004 → Download → Terminate

Result: 1.8x speedup, all videos downloaded automatically
```

## 📊 Fargate Configuration Options

Choose the right performance level for your workload:

```python
# Economy: 1 vCPU, 2GB RAM (~$0.044/hour) - Light workloads
processor = FargateOperationV1(config_priority=5)

# Standard: 2 vCPU, 4GB RAM (~$0.088/hour) - Most common choice
processor = FargateOperationV1(config_priority=1)  # Default

# High Performance: 4 vCPU, 8GB RAM (~$0.175/hour) - Heavy scenes
processor = FargateOperationV1(config_priority=2)

# Ultra Performance: 8 vCPU, 16GB RAM (~$0.351/hour) - Maximum speed
processor = FargateOperationV1(config_priority=3)

# Maximum Performance: 16 vCPU, 32GB RAM (~$0.702/hour) - Enterprise
processor = FargateOperationV1(config_priority=4)
```

## 🎬 Complete Example (Production Ready)

See [`example_usage.py`](./example_usage.py) for comprehensive examples including:
- All CPU configuration options
- Complete API parameter reference
- Single scene processing
- Batch processing examples
- Parallel processing configurations
- Cost optimization strategies

```python
# Quick parallel processing example
from fargate_operation_v1 import execute_parallel_batches

result = execute_parallel_batches(
    scenes=your_scenes,
    scenes_per_batch=3,          # Scenes per container
    max_parallel_tasks=4,        # Concurrent containers
    language="chinese",          # or "english"
    enable_zoom=True,           # Add zoom effects
    config_priority=2,          # High performance config
    saving_dir="./videos"       # Output directory
)

# Automatic results:
# ✅ All videos processed and downloaded
# 💰 Optimal cost distribution across parallel tasks
# 📈 Detailed efficiency and timing metrics
```

## 💡 Key Advantages

### 1. **True Serverless with Parallel Scale**
- **Per-second billing** from container start to finish
- **Multiple concurrent containers** for faster processing
- No risk of forgotten running instances
- Automatic cleanup guaranteed

### 2. **Zero Infrastructure Management**
- No EC2 instances to monitor
- No SSH keys or security patches
- AWS handles all infrastructure and scaling

### 3. **Production Performance**
- **30-second startup** vs 75+ seconds for EC2
- **Parallel processing** across multiple containers
- Intelligent scene distribution and load balancing
- Consistent performance (no "noisy neighbor" issues)

### 4. **Enterprise Ready**
- Built-in high availability and auto-retry
- Integrated with AWS CloudWatch logging
- VPC networking support
- Cost tracking and optimization

## 💰 Cost Comparison

**Example: Processing 8 video scenes**

| Approach | Configuration | Time | Cost | Efficiency |
|----------|---------------|------|------|------------|
| **Sequential (Single Task)** | 2 vCPU | 16 min | $0.024 | 1.0x |
| **🏆 Parallel (4 Tasks × 2 Scenes)** | 2 vCPU each | 9 min | $0.026 | **1.8x faster** |
| **24/7 GPU Server** | Always on | - | ~$500/month | - |

**Key Insight**: Minimal cost increase (8%) for 80% time reduction!

## 🔧 Advanced Features

### Intelligent Scene Distribution
The framework automatically:
- Distributes scenes evenly across parallel tasks
- Handles remainder scenes when batch sizes don't divide evenly
- Optimizes for cost vs speed based on your configuration

### Real-time Monitoring
```python
# Built-in cost tracking and performance metrics
result = execute_parallel_batches(scenes=scenes, ...)

print(f"Tasks used: {result['tasks_used']}")
print(f"Processing efficiency: {result['efficiency']['processing_efficiency']:.1f}%")
print(f"Speedup factor: {result['efficiency']['speedup_factor']:.2f}x")
print(f"Cost per scene: ${result['total_cost_usd']/len(scenes):.4f}")
```

### Flexible Configuration
```python
# Environment variables or .env file
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SUBNET_ID=subnet-xxxxxxxxx
AWS_SECURITY_GROUP_ID=sg-xxxxxxxxx
ECS_CLUSTER_NAME=cloudburst-cluster
ECS_TASK_DEFINITION=cloudburst-task
```

## 🛠️ File Structure

After cleanup, the project structure is:
```
cloudburst_fargate/
├── fargate_operation_v1.py    # Core Fargate operations and parallel processing
├── example_usage.py           # Complete usage examples and API reference
├── README.md                  # This file
├── README_CN.md              # Chinese documentation
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── Docs/                    # Technical documentation
└── backup_test_files/       # Test files (Git ignored)
```

## 🔧 Troubleshooting

### Common Issues

**Task fails to start:**
- Check subnet and security group IDs in .env
- Ensure subnet has internet access (public subnet or NAT gateway)
- Verify AWS credentials with correct permissions

**Network errors:**
- Security group must allow outbound HTTPS (port 443) for Docker pulls
- Security group must allow inbound TCP port 5000 for API access

**Permission errors:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Required IAM permissions: ECS, ECR, CloudWatch, EC2 (for VPC)

### Debug Mode
```python
# Enable detailed AWS logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or check CloudWatch logs: /ecs/cloudburst
```

## 🎯 Roadmap

- [x] **✅ Parallel Processing**: Multiple concurrent Fargate tasks
- [ ] **Fargate Spot**: 70% cost reduction for non-critical workloads  
- [ ] **Auto-scaling**: Dynamic resource allocation based on queue size
- [ ] **S3 Integration**: Direct file transfer without local downloads
- [ ] **Webhook Support**: Real-time notifications when processing completes
- [ ] **GPU Support**: Fargate GPU instances for AI-intensive workloads

## 📄 License

MIT License - Same as the original CloudBurst project

---

**From single-task processing to parallel serverless scale - CloudBurst Fargate is production ready!** 🚀

*Stop managing infrastructure, start processing videos at scale.*