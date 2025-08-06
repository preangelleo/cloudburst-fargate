# Instant Instance Operation

My second open source project! 🚀

[中文版](./README_CN.md)

## What is this?

A Python framework that **automatically manages AWS EC2 instances** for on-demand video generation tasks. 

**Core Value**: When your application needs to generate videos (using our [Video Generation API](https://github.com/preangelleo/video-generation-docker)), this framework:
- 🚀 Spins up an EC2 instance with the video generation Docker container
- 🎬 Processes your video generation requests in parallel
- 📥 Downloads the completed videos
- 🛑 Immediately terminates the instance to save costs
- 💰 You only pay for the actual processing time (minutes, not months!)

**Perfect for**: Production applications that need to generate videos as part of their workflow but don't want to maintain 24/7 GPU instances.

## 🔗 Related Project

This project builds on my first open source project: [**Video Generation API**](https://github.com/preangelleo/video-generation-docker)

- **Video Generation API**: Run a persistent Docker container for video generation (pay monthly)
- **This Project**: Create on demand, ready when needed; shut down after use, pay by the second

Choose based on your needs:
- Frequent usage → Use Video Generation API (persistent container)
- Occasional usage → Use this framework (create on demand, ready when needed; shut down after use, pay by the second)

## 🎯 The Problem It Solves

Running cloud instances 24/7 is expensive. This framework:
- ✅ Creates instance only when needed
- ✅ Runs your task (e.g., video generation)
- ✅ Downloads results
- ✅ Terminates instance automatically
- ✅ Shows exact cost (e.g., $0.018 for 15 videos)

**You pay by the minute, not by the month!**

## 📋 Prerequisites

Before you start, make sure you have:

### 1. AWS Account with Required Permissions
- **AWS Access Key ID** and **AWS Secret Access Key**
- IAM permissions for:
  - EC2 (create, terminate, describe instances)
  - VPC (security groups, subnets)
  - EC2 Pricing API access

### 2. AWS Resources (Must Create in AWS Console First)
- **EC2 Key Pair** - for SSH access to instances (create in EC2 → Key Pairs)
- **Security Group** - with port 5000 open for API access (create in EC2 → Security Groups)
- **VPC Subnet ID** - where instances will be launched (find in VPC → Subnets)

### 3. Local Requirements
- Python 3.7+
- pip (Python package manager)
- Internet connection for AWS API calls

### 4. AWS Credentials Setup

The framework uses boto3, which automatically finds AWS credentials in this order:

1. **Environment variables** (recommended for production)
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

2. **AWS CLI configuration** (if you have AWS CLI installed)
```bash
aws configure
```

3. **AWS credentials file** (automatically created by AWS CLI)
```
~/.aws/credentials
```

**Note**: You don't need to create any files manually. Just set the environment variables or use AWS CLI.

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/preangelleo/cloudburst
cd cloudburst
pip install -r requirements.txt
```

### 2. Configure

Create `.env` file:
```env
# AWS Settings
AWS_REGION=us-east-1
AWS_KEY_PAIR_NAME=your-keypair-name
AWS_SECURITY_GROUP_ID=sg-xxxxxxxxx
AWS_SUBNET_ID=subnet-xxxxxxxxx

# Optional: specific AMI or instance type
AWS_INSTANCE_TYPE=c5.2xlarge
DOCKER_IMAGE=betashow/video-generation-api:latest
```

### 3. Use It

```python
from instant_instance_operation_v2 import InstantInstanceOperationV2

# Initialize
operation = InstantInstanceOperationV2()

# Create instance, run task, terminate
instance_id, instance_ip = operation.create_instance()

# Deploy your Docker container
operation.deploy_and_run_docker(
    instance_ip=instance_ip,
    docker_image="your-docker-image:latest"
)

# Call your API
response = operation.call_api(
    api_url=f"http://{instance_ip}:5000/your-endpoint",
    request_data={"your": "data"}
)

# Download results
operation.download_file(
    instance_ip=instance_ip,
    remote_path="/results/output.zip",
    local_path="./output.zip"
)

# Terminate and get cost
total_cost = operation.terminate_instance()
print(f"Total cost: ${total_cost:.4f}")
```

## 📊 Real Example - Video Generation

### Method 1: Automatic Folder Scanning

**Required folder structure**:
```
video_scenes/
├── images/
│   ├── scene_001_chinese.png
│   └── scene_002_chinese.png
├── audio/
│   ├── scene_001_chinese.mp3
│   ├── scene_002_chinese.mp3
│   ├── scene_001_chinese.srt (optional)
│   └── scene_002_chinese.srt (optional)
```

**Note**: Files must follow naming pattern `scene_XXX_chinese.*` or `scene_XXX_english.*`

```python
from instant_instance_operation_v2 import scan_and_test_folder

result = scan_and_test_folder(
    folder_path="./video_scenes/",
    language="chinese",
    enable_zoom=True
)

print(f"✅ Generated {result['successful_scenes']} videos")
print(f"💰 Total cost: ${result['cost_usd']:.4f}")
```

### 🎬 Output Examples

Here's what you can expect from the generated videos:

**English Example**:
[![English Video Example](https://img.youtube.com/vi/JiWsyuyw1ao/maxresdefault.jpg)](https://www.youtube.com/watch?v=JiWsyuyw1ao)

**Chinese Example**:
[![Chinese Video Example](https://img.youtube.com/vi/WYFyUAk9F6k/maxresdefault.jpg)](https://www.youtube.com/watch?v=WYFyUAk9F6k)

**Video Features Demonstrated**:
- ✅ Professional subtitles with background
- ✅ Smooth zoom effects (Ken Burns effect)
- ✅ Synchronized audio and visuals
- ✅ High-quality video output (1080p)

Both examples show the "Full Featured" mode with subtitles and effects enabled.

### Method 2: Custom Scene List (More Flexible)

```python
from instant_instance_operation_v2 import InstantInstanceOperationV2

# Initialize
operation = InstantInstanceOperationV2()

# Define your scenes with any file paths
scenes = [
    {
        "scene_name": "intro_video",
        "input_image": "/path/to/intro.png",
        "input_audio": "/path/to/intro.mp3",
        "subtitle": "/path/to/intro.srt"  # Optional, can be None
    },
    {
        "scene_name": "main_content",
        "input_image": "/path/to/main.png", 
        "input_audio": "/path/to/main.mp3",
        "subtitle": None  # No subtitle for this scene
    }
]

# Process scenes
result = operation.execute_batch_test(
    scenes=scenes,
    language="english",
    enable_zoom=True
)

print(f"✅ Processed {result['successful_scenes']} videos")
print(f"💰 Total cost: ${result['cost_usd']:.4f}")

# Output example:
# ✅ Processed 2 videos
# 💰 Total cost: $0.0187
```

## 💡 Key Features

### 1. **Smart Instance Management**
- Automatic fallback to alternative instance types
- Handles AWS quota limits gracefully
- Supports spot instances (coming soon)

### 2. **Real-time Cost Tracking**
- Uses AWS Pricing API for accurate costs
- Tracks runtime down to the second
- Returns cost as simple float for easy billing

### 3. **Built for Automation**
- Clean Python dictionary return format
- Ready for database storage
- Perfect for CI/CD pipelines

### 4. **Production Ready**
- Comprehensive error handling
- Automatic cleanup on failure
- Detailed progress logging

## 📈 Use Cases

- **🎬 Video/Audio Processing** - Process media files on GPU instances
- **🤖 ML Model Training** - Train models without 24/7 GPU costs
- **📊 Data Processing** - Run big data jobs on demand
- **🧪 Testing & CI/CD** - Spin up test environments automatically
- **🎨 Rendering** - 3D rendering, image processing

## 🛠️ Advanced Configuration

### Instance Priority (Automatic Fallback)
```python
# Configure in __init__ method
self.instance_configs = [
    {
        "priority": 1,
        "instance_type": "c5.2xlarge",   # CPU optimized
        "description": "Compute optimized - 8 vCPU, 16GB RAM",
        "hourly_cost": "$0.475/hour"     # ~$0.008/minute
    },
    {
        "priority": 2, 
        "instance_type": "m5.xlarge",    # Memory optimized
        "description": "Memory optimized - 4 vCPU, 16GB RAM",
        "hourly_cost": "$0.192/hour"     # ~$0.003/minute
    },
    {
        "priority": 3,
        "instance_type": "g4dn.xlarge",  # GPU for ML/video
        "description": "NVIDIA T4 - 4 vCPU, 16GB RAM, 16GB GPU",
        "hourly_cost": "$0.526/hour"     # ~$0.009/minute
    }
]
```

### 💰 AWS Instance Pricing Reference
*Last updated: August 6, 2025 20:23 UTC | Region: us-east-1 (N. Virginia) | Linux On-Demand*

| Instance Type | vCPU | RAM | GPU | Hourly Cost | Per Minute | 25-min Job |
|--------------|------|-----|-----|-------------|------------|------------|
| **c5.2xlarge** ⭐ | 8 | 16GB | - | $0.475 | $0.0079 | $0.20 |
| **m5.xlarge** | 4 | 16GB | - | $0.192 | $0.0032 | $0.08 |
| **g4dn.xlarge** | 4 | 16GB | T4 16GB | $0.526 | $0.0088 | $0.22 |
| t3.xlarge | 4 | 16GB | - | $0.234 | $0.0039 | $0.10 |
| t3.large | 2 | 8GB | - | $0.083 | $0.0014 | $0.03 |
| c5.xlarge | 4 | 8GB | - | $0.170 | $0.0028 | $0.07 |
| m5.large | 2 | 8GB | - | $0.164 | $0.0027 | $0.07 |
| c5.4xlarge | 16 | 32GB | - | $6.680 | $0.1113 | $2.78 |
| g4dn.2xlarge | 8 | 32GB | T4 16GB | $0.752 | $0.0125 | $0.31 |

⭐ = Default/Recommended instance type

**Note**: Prices are for Linux On-Demand instances. Spot instances can be 50-90% cheaper. Prices may vary by region.

### Return Format for Developers
```python
{
    "success": True,
    "cost_usd": 0.0187,              # Direct float for billing
    "total_time": 385.2,             # Seconds
    "successful_scenes": 15,         # For batch operations
    "batch_results": [               # Individual results
        {
            "scene_name": "scene_001",
            "success": True,
            "download_url": "http://...",
            "processing_time": 18.5
        }
    ]
}
```

## 📋 Requirements

- Python 3.7+
- AWS Account with EC2 permissions
- boto3, requests, python-dotenv

## 🤝 Contributing

This is my second open source project! Feel free to:
- Report bugs
- Suggest features  
- Submit PRs
- Star if you find it useful! ⭐

## 📊 Real Production Benchmarks

Based on actual production testing with AWS EC2 c5.2xlarge instance:

### Video Generation Performance
- **Workload**: 15 scenes (4 different scenarios)
- **Total Runtime**: ~25 minutes
- **Total Cost**: $0.20 USD
- **Instance Setup Time**: ~2 minutes (from launch to ready)
- **Processing**: 60 videos generated
- **Success Rate**: 100%

### Cost Breakdown
```
Instance Launch & Setup: ~2 minutes
Video Processing: ~23 minutes  
Instance Termination: <1 minute
--------------------------------
Total Time: 25 minutes
Total Cost: $0.20 (@ $0.475/hour)
```

### Scenario Performance
| Scenario | Videos | Avg Time/Video | Total Time | File Size |
|----------|--------|----------------|------------|-----------|
| Baseline | 15 | 6.5s | 2.2 min | ~0.8MB each |
| Subtitles Only | 15 | 6.7s | 2.4 min | ~0.8MB each |
| Effects Only | 15 | 34.0s | 9.3 min | ~3.5MB each |
| Full Featured | 15 | 34.5s | 9.6 min | ~3.5MB each |

### 💡 Cost Comparison
- **Traditional 24/7 GPU Instance**: ~$500/month
- **CloudBurst (100 batches/month)**: ~$20/month
- **Savings**: 96% cost reduction!

**Real "Plug and Play" Experience**: From zero to 60 videos in 25 minutes for just $0.20!

## 📄 License

MIT License

---

**Stop paying for idle cloud instances - use them only when you need them!**