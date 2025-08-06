#!/usr/bin/env python3
"""
Continue Docker test after instance is ready
This script continues the test using the already-created instance
"""

import os
import sys
import time
import json
import base64
from datetime import datetime
import paramiko

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instant_instance_operation.instant_instance_operation_v2 import InstantInstanceOperation

def load_instance_info():
    """Load instance info from saved file"""
    info_file = "/Users/lgg/coding/sumatman/runpod/Temps/docker_test_instance.json"
    
    if not os.path.exists(info_file):
        raise Exception(f"Instance info file not found: {info_file}\nPlease run start_instance_for_docker_test.py first")
    
    with open(info_file, "r") as f:
        return json.load(f)

def continue_docker_test():
    """Continue the Docker test with the existing instance"""
    
    # Load instance info
    instance_info = load_instance_info()
    instance_id = instance_info['instance_id']
    instance_ip = instance_info['instance_ip']
    
    print("\n=== Continuing Docker Test ===")
    print(f"Instance ID: {instance_id}")
    print(f"Instance IP: {instance_ip}")
    print(f"Created at: {instance_info['created_at']}")
    
    # Initialize operation handler with existing instance
    operation = InstantInstanceOperation(
        project_name="docker-test",
        region='us-east-1'
    )
    
    # Set the instance details
    operation.instance_id = instance_id
    operation.instance_ip = instance_ip
    
    try:
        # Step 1: Check if instance is ready
        print("\n1. Checking instance connectivity...")
        
        # Test SSH connection
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        max_retries = 3
        for i in range(max_retries):
            try:
                ssh_client.connect(
                    hostname=instance_ip,
                    username='ubuntu',
                    key_filename=os.path.expanduser('~/.ssh/video-generation-gpu-key.pem'),
                    timeout=30
                )
                print("   ✓ SSH connection successful")
                ssh_client.close()
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"   Connection attempt {i+1} failed, retrying...")
                    time.sleep(10)
                else:
                    raise Exception(f"Cannot connect to instance: {e}")
        
        # Step 2: Setup Docker
        print("\n2. Setting up Docker on instance...")
        
        # Install Docker
        print("   Installing Docker...")
        docker_install_script = """
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
"""
        operation._execute_ssh_command(docker_install_script)
        
        # Step 3: Pull Docker image
        print("\n3. Pulling Docker image...")
        print("   This may take a few minutes...")
        pull_command = "sudo docker pull betashow/video-generation-api:latest"
        output = operation._execute_ssh_command(pull_command)
        print("   ✓ Docker image pulled")
        
        # Step 4: Run Docker container
        print("\n4. Starting Docker container...")
        run_command = "sudo docker run -d -p 5000:5000 --name video-api betashow/video-generation-api:latest"
        operation._execute_ssh_command(run_command)
        
        # Wait for container to be ready
        print("   Waiting for container to be ready...")
        time.sleep(10)
        
        # Check container status
        check_command = "sudo docker ps"
        output = operation._execute_ssh_command(check_command)
        if "video-api" in output and "Up" in output:
            print("   ✓ Container is running")
        else:
            print("   ⚠️  Container status unclear:")
            print(output)
        
        # Step 5: Test Full Featured scenario
        print("\n5. Testing Full Featured scenario...")
        
        # Prepare test files
        test_dir = "/Users/lgg/coding/sumatman/runpod/Temps"
        
        # Read input files
        with open(os.path.join(test_dir, "scene_009_chinese.png"), "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        with open(os.path.join(test_dir, "scene_009_chinese.mp3"), "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()
            
        with open(os.path.join(test_dir, "scene_009_chinese.srt"), "rb") as f:
            subtitle_data = base64.b64encode(f.read()).decode()
        
        # Create request
        request_data = {
            "input_image": image_data,
            "input_audio": audio_data,
            "subtitle": subtitle_data,
            "effects": ["zoom_in"],
            "language": "chinese",
            "background_box": True,
            "background_opacity": 0.7,
            "output_filename": "test_full_featured_docker.mp4"
        }
        
        # Save request for debugging
        debug_request_path = os.path.join(test_dir, "docker_test_request.json")
        with open(debug_request_path, "w") as f:
            json.dump(request_data, f, indent=2)
        print(f"   Request saved to: {debug_request_path}")
        
        # Test the API
        api_url = f"http://{instance_ip}:5000"
        
        # Make the API call
        print("\n6. Calling API...")
        start_time = time.time()
        response_data, download_path = operation.call_api_and_download(
            api_url=api_url,
            request_data=request_data,
            output_filename="test_full_featured_docker.mp4"
        )
        elapsed_time = time.time() - start_time
        
        print(f"\n7. Test Results:")
        print(f"   Scenario detected: {response_data.get('scenario', 'unknown')}")
        print(f"   Processing time: {elapsed_time:.2f} seconds")
        print(f"   Video size: {response_data.get('size', 0)} bytes")
        print(f"   Video downloaded to: {download_path}")
        
        # Check if test passed
        test_passed = response_data.get('scenario') == 'full_featured'
        
        if not test_passed:
            print("\n⚠️  TEST FAILED: Scenario not detected as 'full_featured'")
            print(f"   Detected as: '{response_data.get('scenario', 'unknown')}'")
            print("\n8. Extracting app.py from Docker image for analysis...")
            
            # Extract app.py from Docker container
            extract_commands = [
                "sudo docker cp video-api:/app/app.py /tmp/docker_app.py",
                "cat /tmp/docker_app.py > /tmp/docker_app_content.txt"
            ]
            
            for cmd in extract_commands:
                operation._execute_ssh_command(cmd)
            
            # Download the file
            docker_app_path = os.path.join(test_dir, "docker_app.py")
            operation._download_file("/tmp/docker_app.py", docker_app_path)
            print(f"   Docker app.py saved to: {docker_app_path}")
            
            # Check for the fix
            with open(docker_app_path, "r") as f:
                docker_app_content = f.read()
            
            if "# Recalculate for scenario detection" in docker_app_content:
                print("\n   ✓ Fix IS present in Docker app.py")
                print("   This suggests a different issue than expected")
            else:
                print("\n   ✗ Fix is NOT present in Docker app.py")
                print("   The Docker image needs to be rebuilt with the fixed app.py")
            
            # Get container logs
            print("\n9. Getting container logs...")
            logs_command = "sudo docker logs video-api --tail 50"
            logs = operation._execute_ssh_command(logs_command)
            
            logs_path = os.path.join(test_dir, "docker_container_logs.txt")
            with open(logs_path, "w") as f:
                f.write(logs)
            print(f"   Logs saved to: {logs_path}")
            
            print("\n⚠️  KEEPING INSTANCE ALIVE for further investigation")
            print(f"\n   Instance ID: {instance_id}")
            print(f"   Instance IP: {instance_ip}")
            print(f"   SSH: ssh -i ~/.ssh/video-generation-gpu-key.pem ubuntu@{instance_ip}")
            print("\n   To terminate manually: python3 terminate_docker_test_instance.py")
            
            # Save test results
            results = {
                "test_passed": False,
                "scenario_detected": response_data.get('scenario', 'unknown'),
                "instance_id": instance_id,
                "instance_ip": instance_ip,
                "docker_app_has_fix": "# Recalculate for scenario detection" in docker_app_content,
                "elapsed_time": elapsed_time,
                "response_data": response_data,
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            print("\n✅ TEST PASSED: Full Featured scenario correctly detected!")
            
            # Get running cost
            total_cost = operation.calculate_running_cost()
            print(f"\n8. Instance running cost: ${total_cost:.6f}")
            
            print("\n9. Terminating instance...")
            operation.terminate_instance()
            
            # Save test results
            results = {
                "test_passed": True,
                "scenario_detected": "full_featured",
                "instance_terminated": True,
                "total_cost": total_cost,
                "elapsed_time": elapsed_time,
                "response_data": response_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Remove instance info file
            os.remove(instance_info_file)
            print("   ✓ Instance terminated and cleaned up")
        
        # Save results
        results_path = os.path.join(test_dir, f"docker_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nTest results saved to: {results_path}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        
        # Don't terminate on error - keep for debugging
        print(f"\nInstance kept alive for debugging:")
        print(f"   Instance ID: {instance_id}")
        print(f"   Instance IP: {instance_ip}")
        print(f"   SSH: ssh -i ~/.ssh/video-generation-gpu-key.pem ubuntu@{instance_ip}")
        
        raise


def main():
    """Main function"""
    print("Docker Test Continuation")
    print("=======================")
    
    # Check if instance info exists
    info_file = "/Users/lgg/coding/sumatman/runpod/Temps/docker_test_instance.json"
    if not os.path.exists(info_file):
        print(f"\n❌ No instance info found at: {info_file}")
        print("Please run start_instance_for_docker_test.py first")
        return
    
    # Load and display instance info
    instance_info = load_instance_info()
    print(f"\nFound instance:")
    print(f"  ID: {instance_info['instance_id']}")
    print(f"  IP: {instance_info['instance_ip']}")
    print(f"  Created: {instance_info['created_at']}")
    
    # Run the test
    try:
        results = continue_docker_test()
        
        if results['test_passed']:
            print("\n🎉 Docker image test completed successfully!")
            print("The Full Featured scenario is working correctly.")
        else:
            print("\n⚠️  Docker image test failed")
            print("Instance kept alive for investigation")
            print("\nNext steps:")
            print("1. Check docker_app.py in Temps folder")
            print("2. Run: python3 compare_app_versions.py")
            print("3. If fix missing, rebuild Docker image")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()