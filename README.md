# Instant Instance Operation

My second open source project! 🚀

[中文版](./README_CN.md)

## What is this?

A Python framework that **automatically manages AWS EC2 instances** for on-demand video generation tasks. 

**Core Value**: When your application needs to generate videos (using our [Video Generation API](https://github.com/betashow/video-generation-docker)), this framework:
- 🚀 Spins up an EC2 instance with the video generation Docker container
- 🎬 Processes your video generation requests in parallel
- 📥 Downloads the completed videos
- 🛑 Immediately terminates the instance to save costs
- 💰 You only pay for the actual processing time (minutes, not months!)

**Perfect for**: Production applications that need to generate videos as part of their workflow but don't want to maintain 24/7 GPU instances.

## 🔗 Related Project

This project builds on my first open source project: [**Video Generation API**](https://github.com/betashow/video-generation-docker)

- **Video Generation API**: Run a persistent Docker container for video generation (pay monthly)
- **This Project**: Create instances on-demand for video generation (pay per minute)

Choose based on your needs:
- Frequent usage → Use Video Generation API (persistent container)
- Occasional usage → Use this framework (on-demand instances)

## 🎯 The Problem It Solves

Running cloud instances 24/7 is expensive. This framework:
- ✅ Creates instance only when needed
- ✅ Runs your task (e.g., video generation)
- ✅ Downloads results
- ✅ Terminates instance automatically
- ✅ Shows exact cost (e.g., $0.018 for 15 videos)

**You pay by the minute, not by the month!**

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/your-username/instant-instance-operation
cd instant-instance-operation
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
AWS_INSTANCE_TYPE=t3.xlarge
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

```python
# Example: Generate 15 videos with effects
from instant_instance_operation_v2 import scan_and_test_folder

result = scan_and_test_folder(
    folder_path="./video_scenes/",
    language="chinese",
    enable_zoom=True
)

# Results you get:
print(f"✅ Generated {result['successful_scenes']} videos")
print(f"💰 Total cost: ${result['cost_usd']:.4f}")
print(f"⏱️  Total time: {result['total_time']:.1f} seconds")

# Output:
# ✅ Generated 15 videos
# 💰 Total cost: $0.0187
# ⏱️  Total time: 385.2 seconds
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
        "instance_type": "g4dn.xlarge",  # GPU for ML/video
        "description": "NVIDIA T4 GPU"
    },
    {
        "priority": 2, 
        "instance_type": "c5.2xlarge",   # High CPU
        "description": "Compute optimized"
    },
    {
        "priority": 3,
        "instance_type": "t3.xlarge",    # Balanced
        "description": "General purpose"
    }
]
```

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