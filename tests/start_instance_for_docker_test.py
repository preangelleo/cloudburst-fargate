#!/usr/bin/env python3
"""
Start AWS instance for Docker testing
This script starts the instance and returns immediately so we can do other tasks while it boots
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instant_instance_operation.instant_instance_operation_v2 import InstantInstanceOperation

def start_instance():
    """Start an AWS instance and return its details"""
    
    # Initialize the operation handler
    operation = InstantInstanceOperation(
        project_name="docker-test",
        region='us-east-1'
    )
    
    print("\n=== Starting AWS Instance for Docker Testing ===")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Create instance
        print("\nCreating AWS instance...")
        instance_id, instance_ip = operation.create_instance(instance_type='t3.large')
        
        print(f"\n✅ Instance created successfully!")
        print(f"   Instance ID: {instance_id}")
        print(f"   Public IP: {instance_ip}")
        print(f"   Region: us-east-1")
        print(f"   Type: t3.large")
        
        # Save instance details for later use
        instance_info = {
            "instance_id": instance_id,
            "instance_ip": instance_ip,
            "region": "us-east-1",
            "created_at": datetime.now().isoformat(),
            "ssh_command": f"ssh -i ~/.ssh/video-generation-gpu-key.pem ubuntu@{instance_ip}",
            "status": "booting"
        }
        
        # Save to file
        info_file = "/Users/lgg/coding/sumatman/runpod/Temps/docker_test_instance.json"
        with open(info_file, "w") as f:
            json.dump(instance_info, f, indent=2)
        
        print(f"\n📁 Instance info saved to: {info_file}")
        print(f"\n🚀 Instance is now booting up...")
        print("   While waiting, you can:")
        print("   1. Rebuild the Docker image with: python3 /Users/lgg/coding/sumatman/runpod/video_generation/rebuild_and_push_docker.py")
        print("   2. The instance will be ready in ~2-3 minutes")
        print(f"\n   SSH command (for later): {instance_info['ssh_command']}")
        
        return instance_id, instance_ip
        
    except Exception as e:
        print(f"\n❌ Error creating instance: {str(e)}")
        raise


def main():
    """Main function"""
    print("AWS Instance Launcher for Docker Testing")
    print("======================================")
    
    # Start the instance
    try:
        instance_id, instance_ip = start_instance()
        
        print("\n" + "="*60)
        print("INSTANCE STARTED - Now you can rebuild the Docker image")
        print("="*60)
        print("\nNext steps:")
        print("1. Rebuild Docker image (while instance boots):")
        print("   cd /Users/lgg/coding/sumatman/runpod/video_generation")
        print("   python3 rebuild_and_push_docker.py")
        print("\n2. After ~3 minutes, continue with the test:")
        print("   cd /Users/lgg/coding/sumatman/runpod/instant_instance_operation") 
        print("   python3 continue_docker_test.py")
        
    except Exception as e:
        print(f"\n❌ Failed to start instance: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()