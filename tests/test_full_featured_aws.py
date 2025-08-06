#!/usr/bin/env python3
"""
Full Featured Test for InstantInstanceOperation v2
Creates AWS instance, tests video generation with effects + subtitles, downloads result, and terminates
"""

import os
import sys
import json
import time
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instant_instance_operation_v2 import InstantInstanceOperationV2

def test_full_featured():
    """Test Full Featured video generation with AWS instance"""
    print("🎬 Full Featured Video Generation Test (AWS Instance)")
    print("=" * 70)
    
    # Configuration
    test_files_dir = "/Users/lgg/coding/sumatman/runpod/Temps"
    output_dir = os.path.join(test_files_dir, "test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare single scene for test
    scene = {
        "scene_name": "scene_009_chinese",
        "input_image": os.path.join(test_files_dir, "scene_009_chinese.png"),
        "input_audio": os.path.join(test_files_dir, "scene_009_chinese.mp3"),
        "subtitle": os.path.join(test_files_dir, "scene_009_chinese.srt")
    }
    
    # Verify files exist
    print("\n📁 Verifying test files...")
    for file_type, path in [("Image", scene["input_image"]), 
                            ("Audio", scene["input_audio"]), 
                            ("Subtitle", scene["subtitle"])]:
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f"✅ {file_type}: {os.path.basename(path)} ({size:.1f} KB)")
        else:
            print(f"❌ {file_type} not found: {path}")
            return
    
    # Initialize operation with instance configuration
    print("\n🔧 Initializing InstantInstanceOperation v2...")
    try:
        # Use priority 1 (c5.2xlarge) for better performance
        operation = InstantInstanceOperationV2(config_priority=1)
        print(f"✅ Configured for: {operation.config_name}")
        print(f"   Instance type: {operation.instance_type}")
        print(f"   Description: {operation.current_config['description']}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📝 Please create a .env file with:")
        print("AWS_REGION=us-east-1")
        print("AWS_AMI_ID=ami-021589336d307b577")
        print("AWS_KEY_PAIR_NAME=your-key-pair-name")
        print("AWS_SECURITY_GROUP_ID=sg-xxxxxxxxxxxxxxxxx")
        print("AWS_SUBNET_ID=subnet-xxxxxxxxxxxxxxxx")
        print("DOCKER_IMAGE=betashow/video-generation-api:latest")
        return
    
    # Test parameters
    test_params = {
        "scenes": [scene],  # Single scene for this test
        "language": "chinese",
        "enable_zoom": True  # Enable effects for Full Featured
    }
    
    print("\n🎯 Test Configuration:")
    print(f"   Scenario: Full Featured (Effects + Subtitles)")
    print(f"   Language: {test_params['language']}")
    print(f"   Effects: Zoom enabled")
    print(f"   Subtitles: Enabled")
    
    # Execute batch test
    print("\n🚀 Starting AWS instance and video generation...")
    print("   This will:")
    print("   1. Create AWS EC2 instance")
    print("   2. Deploy Docker container") 
    print("   3. Generate video with effects + subtitles")
    print("   4. Keep instance alive for downloads")
    
    start_time = time.time()
    
    try:
        # Execute the batch test
        result = operation.execute_batch_test(**test_params)
        
        if result["success"]:
            print(f"\n✅ Video generation successful!")
            print(f"   Scenes processed: {result['successful_scenes']}/{result['total_scenes']}")
            print(f"   Processing time: {result['total_time']:.1f}s")
            print(f"   Instance ID: {result['instance_id']}")
            print(f"   Public IP: {result['public_ip']}")
            print(f"   Current cost: ${result['cost_usd']:.6f}")
            
            # Show batch results
            print("\n📊 Generation Results:")
            for i, scene_result in enumerate(result['batch_results'], 1):
                if scene_result.get('success'):
                    print(f"   Scene {i}: ✅ {scene_result['scene_name']}")
                    print(f"      - File ID: {scene_result['file_id']}")
                    print(f"      - Size: {scene_result['file_size']/1024/1024:.2f} MB")
                    print(f"      - Processing: {scene_result['processing_time']:.1f}s")
                    print(f"      - Scenario: {scene_result['scenario']}")
                else:
                    print(f"   Scene {i}: ❌ {scene_result.get('error', 'Unknown error')}")
            
            # Download results
            print("\n📥 Downloading generated videos...")
            download_result = operation.download_batch_results(
                batch_results=result['batch_results'],
                output_dir=output_dir,
                instance_id=result['instance_id']
            )
            
            print(f"\n✅ Downloads completed!")
            print(f"   Downloaded: {download_result['download_count']}/{download_result['total_available']}")
            print(f"   Final cost: ${download_result['final_cost_usd']:.6f}")
            
            # Show downloaded files
            if download_result['downloaded_files']:
                print("\n📁 Downloaded files:")
                for filepath in download_result['downloaded_files']:
                    print(f"   - {filepath}")
            
            # Save test report
            report_file = os.path.join(output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            report_data = {
                "test_type": "full_featured",
                "test_time": datetime.now().isoformat(),
                "total_time": time.time() - start_time,
                "aws_instance": {
                    "instance_id": result['instance_id'],
                    "instance_type": operation.instance_type,
                    "public_ip": result['public_ip']
                },
                "processing_results": {
                    "total_scenes": result['total_scenes'],
                    "successful_scenes": result['successful_scenes'],
                    "processing_time": result['total_time'],
                    "avg_time_per_scene": result.get('avg_processing_time', 0)
                },
                "cost_analysis": {
                    "processing_cost_usd": result['cost_usd'],
                    "final_cost_usd": download_result['final_cost_usd'],
                    "instance_hourly_rate": result['cost_info']['hourly_rate_usd']
                },
                "download_urls": [r['download_url'] for r in result['batch_results'] if r.get('success')],
                "downloaded_files": download_result['downloaded_files']
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n📝 Test report saved: {report_file}")
            
            # Summary
            print("\n" + "=" * 70)
            print("🎉 TEST COMPLETED SUCCESSFULLY!")
            print(f"   Total time: {time.time() - start_time:.1f}s")
            print(f"   Total cost: ${download_result['final_cost_usd']:.6f}")
            print(f"   Output directory: {output_dir}")
            
        else:
            print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
            if result.get('timing_log'):
                print("\n📋 Timing log:")
                for log_entry in result['timing_log'][-10:]:  # Show last 10 entries
                    print(f"   {log_entry}")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Test session ended")


def create_env_template():
    """Create .env template if it doesn't exist"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        template = """# AWS Configuration
AWS_REGION=us-east-1
AWS_AMI_ID=ami-021589336d307b577
AWS_KEY_PAIR_NAME=your-key-pair-name-here
AWS_SECURITY_GROUP_ID=sg-xxxxxxxxxxxxxxxxx
AWS_SUBNET_ID=subnet-xxxxxxxxxxxxxxxx

# Docker Configuration
DOCKER_IMAGE=betashow/video-generation-api:latest

# API Configuration (Optional)
API_TIMEOUT_MINUTES=15
API_REQUEST_TIMEOUT_SECONDS=300
VIDEO_API_AUTH_KEY=

# Results Directory (Optional)
RESULTS_DIR=/tmp/instant_test_results
"""
        with open(env_path, 'w') as f:
            f.write(template)
        print(f"📝 Created .env template at: {env_path}")
        print("   Please edit it with your AWS credentials before running the test.")
        return False
    return True


if __name__ == "__main__":
    print("🚀 Instant Instance Operation v2 - Full Featured Test")
    print("This test will create an AWS instance, generate video with effects + subtitles,")
    print("download the result, and terminate the instance.")
    print("")
    
    # Check for .env file
    if not create_env_template():
        sys.exit(1)
    
    # Check dependencies
    try:
        import boto3
        import requests
        from dotenv import load_dotenv
        # Load .env from the current directory
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(env_path)
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nPlease install required packages:")
        print("pip install boto3 requests python-dotenv")
        sys.exit(1)
    
    # Confirm before proceeding
    print("\n⚠️  This test will:")
    print("   - Create an AWS EC2 instance (charges apply)")
    print("   - Process 1 scene with zoom effects and subtitles")
    print("   - Automatically terminate the instance after completion")
    print(f"   - Estimated cost: ~$0.004-0.006 USD")
    
    response = input("\nProceed with the test? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        test_full_featured()
    else:
        print("Test cancelled.")