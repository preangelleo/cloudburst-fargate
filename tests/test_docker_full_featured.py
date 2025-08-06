#!/usr/bin/env python3
"""
Test Docker Image Full Featured Scenario on AWS
This script will:
1. Create an AWS instance
2. Pull and run the Docker image
3. Test Full Featured scenario (effects + subtitles)
4. If test fails, extract and compare app.py
5. Keep instance alive if issue found
"""

import os
import sys
import time
import json
import base64
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instant_instance_operation.instant_instance_operation_v2 import InstantInstanceOperation

def test_docker_image():
    """Test the Docker image with Full Featured scenario"""
    
    # Initialize the operation handler
    operation = InstantInstanceOperation(
        project_name="docker-test",
        region='us-east-1'
    )
    
    print("\n=== Docker Image Full Featured Test ===")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Create instance
        print("\n1. Creating AWS instance...")
        instance_id, instance_ip = operation.create_instance(instance_type='t3.large')
        print(f"   Instance created: {instance_id}")
        print(f"   Public IP: {instance_ip}")
        
        # Step 2: Setup Docker on instance
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
        
        # Pull the Docker image
        print("\n3. Pulling Docker image...")
        pull_command = "sudo docker pull betashow/video-generation-api:latest"
        operation._execute_ssh_command(pull_command)
        
        # Run the Docker container
        print("\n4. Starting Docker container...")
        run_command = "sudo docker run -d -p 5000:5000 --name video-api betashow/video-generation-api:latest"
        operation._execute_ssh_command(run_command)
        
        # Wait for container to be ready
        print("   Waiting for container to be ready...")
        time.sleep(10)
        
        # Check container status
        check_command = "sudo docker ps"
        output = operation._execute_ssh_command(check_command)
        print(f"   Container status: {output}")
        
        # Step 3: Test Full Featured scenario
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
            "background_opacity": 0.7
        }
        
        # Test the API
        api_url = f"http://{instance_ip}:5000"
        
        # Make the API call
        start_time = time.time()
        response_data, download_path = operation.call_api_and_download(
            api_url=api_url,
            request_data=request_data,
            output_filename="test_full_featured_docker.mp4"
        )
        elapsed_time = time.time() - start_time
        
        print(f"\n6. Test Results:")
        print(f"   Scenario detected: {response_data.get('scenario', 'unknown')}")
        print(f"   Processing time: {elapsed_time:.2f} seconds")
        print(f"   Video downloaded to: {download_path}")
        
        # Check if test passed
        test_passed = response_data.get('scenario') == 'full_featured'
        
        if not test_passed:
            print("\n⚠️  TEST FAILED: Scenario not detected as 'full_featured'")
            print("\n7. Extracting app.py from Docker image for analysis...")
            
            # Extract app.py from Docker container
            extract_commands = [
                "sudo docker cp video-api:/app/app.py /tmp/docker_app.py",
                "cat /tmp/docker_app.py"
            ]
            
            docker_app_content = ""
            for cmd in extract_commands:
                output = operation._execute_ssh_command(cmd)
                if cmd.startswith("cat"):
                    docker_app_content = output
            
            # Save Docker app.py locally for comparison
            docker_app_path = os.path.join(test_dir, "docker_app.py")
            with open(docker_app_path, "w") as f:
                f.write(docker_app_content)
            print(f"   Docker app.py saved to: {docker_app_path}")
            
            # Download using SCP
            operation._download_file("/tmp/docker_app.py", docker_app_path)
            
            # Check for the fix in Docker app.py
            if "# Recalculate for scenario detection" in docker_app_content:
                print("\n   ✓ Fix is present in Docker app.py")
            else:
                print("\n   ✗ Fix is NOT present in Docker app.py")
                print("   The Docker image needs to be rebuilt with the fixed app.py")
            
            print("\n⚠️  KEEPING INSTANCE ALIVE for further investigation")
            print(f"   Instance ID: {instance_id}")
            print(f"   Instance IP: {instance_ip}")
            print("   SSH command: ssh -i ~/.ssh/video-generation-gpu-key.pem ubuntu@" + instance_ip)
            
            # Save test results
            results = {
                "test_passed": False,
                "scenario_detected": response_data.get('scenario', 'unknown'),
                "instance_id": instance_id,
                "instance_ip": instance_ip,
                "docker_app_has_fix": "# Recalculate for scenario detection" in docker_app_content,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            print("\n✅ TEST PASSED: Full Featured scenario correctly detected!")
            print("\n8. Terminating instance...")
            
            # Get final cost
            total_cost = operation.calculate_running_cost()
            
            # Terminate instance
            operation.terminate_instance()
            
            # Save test results
            results = {
                "test_passed": True,
                "scenario_detected": "full_featured",
                "instance_terminated": True,
                "total_cost": total_cost,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat()
            }
        
        # Save results to file
        results_path = os.path.join(test_dir, f"docker_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nTest results saved to: {results_path}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        
        # Try to terminate instance on error
        if 'instance_id' in locals():
            try:
                print("\nTerminating instance due to error...")
                operation.terminate_instance()
            except:
                print(f"Failed to terminate instance {instance_id}")
        
        raise


def main():
    """Main function"""
    print("Docker Image Full Featured Test")
    print("==============================")
    print("\nThis test will:")
    print("1. Create a new AWS instance")
    print("2. Pull the Docker image betashow/video-generation-api:latest")
    print("3. Test Full Featured scenario (effects + subtitles)")
    print("4. If test fails, extract app.py for comparison")
    print("5. Keep instance alive if issue found, terminate if success")
    
    # Confirm before proceeding
    response = input("\nProceed with test? (yes/no): ")
    if response.lower() != 'yes':
        print("Test cancelled.")
        return
    
    # Run the test
    try:
        results = test_docker_image()
        
        if results['test_passed']:
            print("\n🎉 Docker image test completed successfully!")
        else:
            print("\n⚠️  Docker image test failed - instance kept alive for investigation")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()