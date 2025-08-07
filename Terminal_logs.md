# CloudBurst Terminal Logs Examples

This document provides real terminal output examples from CloudBurst operations, with sensitive information sanitized and detailed explanations of what's happening at each step.

## 🔒 Sanitized Information

The following sensitive data has been replaced for security:
- **AWS Instance IDs**: `i-0xxxxxxxxxxxxxxxxx` 
- **Public IPs**: `x.xxx.xxx.xxx`
- **File paths**: `/path/to/project/` instead of actual user paths
- **UUIDs**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## 📊 Example 1: Single Scene Processing

This example shows processing one 27-second Chinese video with subtitles and zoom effects.

### Key Metrics:
- **Input**: 1 scene (27-second audio + image + subtitles)
- **Total Time**: 155.9 seconds (2.6 minutes)
- **Cost**: $0.021 (about 2 cents)
- **Output**: 7.2MB MP4 video

### Terminal Output:
```
~/project % python3 test_cloudburst_auto_download.py
⚠️  WARNING: This will create an AWS EC2 instance and incur charges!
   Estimated cost: ~$0.01-0.02 for a single scene

✨ NEW: auto_terminate=True now downloads files automatically!

Do you want to continue? (yes/no): yes
🚀 Testing CloudBurst with automatic download
============================================================
Scene: scene_024_chinese
Image: scene_024_chinese.png
Audio: scene_024_chinese.mp3
Subtitle: scene_024_chinese.srt
============================================================
⏱️  [08:44:00.763] +  0.00s - === BATCH INSTANT OPERATION START (1 scenes) ===
⏱️  [08:44:00.763] +  0.00s - Starting smart AWS instance creation
⏱️  [08:44:00.763] +  0.00s - 🔍 Checking instance availability before creation...
⏱️  [08:44:01.565] +  0.80s - ✅ Selected instance c5.2xlarge is available in 5 zones
⏱️  [08:44:02.537] +  1.77s - Instance pricing: $0.4750/hour (c5.2xlarge)
⏱️  [08:44:02.537] +  1.77s - 🚀 Attempting to create instance: c5.2xlarge (attempt 1/3)
⏱️  [08:44:04.222] +  3.46s - ✅ Instance created successfully: i-0xxxxxxxxxxxxxxxxx
⏱️  [08:44:04.222] +  3.46s - Waiting for instance to be running...
⏱️  [08:44:10.212] +  9.45s - Instance running at IP: x.xxx.xxx.xxx
⏱️  [08:44:10.212] +  9.45s - Waiting for Docker API to be ready...
⏱️  [08:44:13.404] + 12.64s - Still waiting for API... attempt 1/120
⏱️  [08:45:05.386] + 64.62s - Still waiting for API... attempt 11/120
⏱️  [08:45:16.021] + 75.26s - Docker API is ready and healthy

⏱️  [08:45:16.022] + 75.26s - 📥 AUTO-DOWNLOAD ENABLED: Files will be downloaded automatically before termination

⏱️  [08:45:16.022] + 75.26s - === Processing Scene 1/1 ===
⏱️  [08:45:16.022] + 75.26s - Processing scene: scene_024_chinese
⏱️  [08:45:16.041] + 75.28s - Scene scene_024_chinese: Files encoded (with subtitles)
⏱️  [08:45:16.041] + 75.28s - Scene scene_024_chinese: Using unified API endpoint (expected scenario: full_featured)
⏱️  [08:45:16.041] + 75.28s - Scene scene_024_chinese: Request has effects: ['zoom_in', 'zoom_out'] (enable_zoom=True)
⏱️  [08:45:16.041] + 75.28s - Scene scene_024_chinese: Request has subtitle: True (length=1680 chars)
⏱️  [08:45:16.042] + 75.28s - Scene scene_024_chinese: Sending request to /create_video_onestep...
⏱️  [08:46:36.664] +155.90s - Scene scene_024_chinese: Completed - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (7.17MB) in 80.6s
⏱️  [08:46:36.665] +155.90s - === BATCH PROCESSING COMPLETED: 1/1 scenes successful in 155.90s ===
⏱️  [08:46:36.665] +155.90s - Current estimated cost: $0.020336 (runtime: 2.57min)
⏱️  [08:46:36.665] +155.90s - Auto-downloading results before termination...
⏱️  [08:46:36.665] +155.90s - Downloading scene_024_chinese... (1/1)
⏱️  [08:46:41.726] +160.96s - Downloaded scene_024_chinese: 7.17MB
⏱️  [08:46:41.726] +160.96s - FINAL COST: $0.021004 (total runtime: 2.65min)
⏱️  [08:46:41.726] +160.96s - All downloads completed (1/1), terminating instance...
⏱️  [08:46:41.726] +160.96s - Terminating instance: i-0xxxxxxxxxxxxxxxxx
⏱️  [08:46:42.958] +162.19s - Instance termination initiated

============================================================
📊 CLOUDBURST RESULTS
============================================================
✅ Success: 1/1 scenes processed
💰 Final cost: $0.0210
⏱️  Total time: 155.9 seconds
🖥️  Instance type: c5.2xlarge

📥 Downloaded 1 files automatically!
📁 Output directory: /path/to/project/Temps/instant_test_results/batch_20250807_084636
   🎬 scene_024_chinese_20250807_084641.mp4 (7.2 MB)

✅ Test completed!
```

### Time Breakdown Explanation:

| Phase | Duration | Description |
|-------|----------|-------------|
| **Instance Creation** | 0-10s | AWS provisions the EC2 instance |
| **Docker Setup** | 10-75s | Docker container with video generation API loads |
| **Video Processing** | 75-156s | Actual video generation (80.6s for 27s video) |
| **File Download** | 156-161s | Download 7.2MB video from instance |
| **Instance Termination** | 161-162s | Clean shutdown to stop billing |

### Cost Analysis:
- **Hourly Rate**: $0.475/hour for c5.2xlarge
- **Total Runtime**: 2.65 minutes
- **Final Cost**: $0.021 (2.65 min × $0.475/60)

---

## 📊 Example 2: Parallel Batch Processing (Expected Output)

This example shows what you'll see when running the parallel test with 2 scenes on 2 instances.

### Expected Metrics:
- **Input**: 2 scenes (scene_015 and scene_021)
- **Instances**: 2 (running in parallel)
- **Expected Time**: ~160-180 seconds (similar to single scene due to parallelism)
- **Expected Cost**: ~$0.04-0.05 (2x the single scene cost)
- **Speedup**: ~2x faster than sequential processing

### Expected Terminal Output:
```
~/project % python3 test_cloudburst_parallel_two_instances.py
⚠️  WARNING: This will create 2 AWS EC2 instances and incur charges!
   Estimated cost: ~$0.04-0.05 for 2 scenes on 2 instances

🔄 PARALLEL PROCESSING: Each instance will process 1 scene simultaneously
   This tests the execute_parallel_batches function

Do you want to continue? (yes/no): yes
🚀 Testing CloudBurst PARALLEL processing with 2 instances
============================================================
Scene 1: scene_015_chinese
Scene 2: scene_021_chinese
Processing: 1 scene per instance (2 instances total)
============================================================
✅ All scene files found
============================================================

[PARALLEL EXECUTION BEGINS]
📊 Creating 2 instances in parallel...
   Instance 1: Processing scene_015_chinese
   Instance 2: Processing scene_021_chinese

[Both instances run simultaneously, logs interleaved]

============================================================
📊 PARALLEL CLOUDBURST RESULTS
============================================================
✅ Success: 2/2 scenes processed
💰 Total cost: $0.0420
⏱️  Total time (parallel): 165.3 seconds
⏱️  Time if sequential: 320.5 seconds
🚀 Speedup: 1.9x faster!
🖥️  Instances used: 2

📥 Downloaded 2 files:
   🎬 Batch 1: scene_015_chinese_[timestamp].mp4 (6.8 MB)
   🎬 Batch 2: scene_021_chinese_[timestamp].mp4 (7.5 MB)

🖥️  Instance Details:
   - Batch 1: 1 scenes, $0.0208, c5.2xlarge
   - Batch 2: 1 scenes, $0.0212, c5.2xlarge

✅ Test completed!
```

### Parallel Processing Benefits:

1. **Time Savings**: 
   - Sequential: ~320 seconds (160s × 2)
   - Parallel: ~165 seconds (only slightly more than 1 scene)
   - Savings: ~155 seconds (48% faster)

2. **Cost Implications**:
   - Same total compute time, same total cost
   - But results delivered much faster

3. **Scalability**:
   - 10 scenes on 10 instances: Still ~165 seconds
   - 100 scenes on 20 instances: Still ~165-200 seconds
   - Linear cost, logarithmic time

---

## 🔍 Log Analysis Guide

### Understanding Timestamps:
- `[08:44:00.763]`: Actual wall clock time
- `+ 0.00s`: Elapsed time since start
- Both help track performance and identify bottlenecks

### Key Indicators:
- ✅ Success markers
- ⚠️ Warnings (non-fatal)
- ❌ Errors (operation failed)
- 📥 Download operations
- 💰 Cost tracking
- ⏱️ Performance metrics

### Cost Monitoring:
1. **Current estimated cost**: Cost before downloads
2. **FINAL COST**: Total cost including all operations
3. Always shows 6 decimal places for accuracy

### Instance States:
1. **Creating**: AWS provisioning resources
2. **Running**: Instance is active (billing starts)
3. **API Ready**: Docker container ready for requests
4. **Processing**: Actively generating videos
5. **Downloading**: Transferring results
6. **Terminating**: Shutting down (billing stops)

---

## 💡 Tips for Reading Logs

1. **Setup Time is One-Time**: The ~75s Docker setup happens once per instance, regardless of scenes
2. **Processing Ratio**: Expect ~3 seconds of processing per 1 second of video
3. **Download Speed**: Depends on file size and network, typically 1-2 MB/s
4. **Cost Precision**: Costs are calculated to 6 decimal places for accuracy
5. **Parallel Efficiency**: Best with 5+ scenes per instance to amortize setup time

---

## 🚨 Common Issues in Logs

### "Still waiting for API..."
- Normal during Docker startup
- Concern if continues beyond attempt 20

### "Instance not available in zone"
- AWS capacity issue
- Framework automatically tries other zones

### "Download failed"
- Network timeout
- File will be retried or marked as failed

### Cost higher than expected
- Check "Total runtime" - includes all operations
- Setup time is included in cost
- Consider batching more scenes per instance