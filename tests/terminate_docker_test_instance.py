#!/usr/bin/env python3
"""
Terminate the Docker test instance manually
Use this if you need to clean up the instance after debugging
"""

import os
import sys
import json
import boto3
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instant_instance_operation.instant_instance_operation_v2 import InstantInstanceOperation

def terminate_test_instance():
    """Terminate the Docker test instance"""
    
    # Load instance info
    info_file = "/Users/lgg/coding/sumatman/runpod/Temps/docker_test_instance.json"
    
    if not os.path.exists(info_file):
        print(f"❌ No instance info found at: {info_file}")
        print("Instance may have already been terminated.")
        return
    
    with open(info_file, "r") as f:
        instance_info = json.load(f)
    
    instance_id = instance_info['instance_id']
    instance_ip = instance_info['instance_ip']
    
    print("Docker Test Instance Terminator")
    print("==============================")
    print(f"\nInstance to terminate:")
    print(f"  ID: {instance_id}")
    print(f"  IP: {instance_ip}")
    print(f"  Created: {instance_info['created_at']}")
    
    # Confirm termination
    response = input("\nAre you sure you want to terminate this instance? (yes/no): ")
    if response.lower() != 'yes':
        print("Termination cancelled.")
        return
    
    # Initialize operation handler
    operation = InstantInstanceOperation(
        project_name="docker-test",
        region='us-east-1'
    )
    
    # Set instance details
    operation.instance_id = instance_id
    operation.instance_ip = instance_ip
    
    try:
        # Calculate final cost
        print("\nCalculating instance cost...")
        total_cost = operation.calculate_running_cost()
        print(f"Total running cost: ${total_cost:.6f}")
        
        # Terminate instance
        print("\nTerminating instance...")
        operation.terminate_instance()
        
        # Remove instance info file
        os.remove(info_file)
        print("✓ Instance info file removed")
        
        print(f"\n✅ Instance {instance_id} terminated successfully!")
        print(f"Final cost: ${total_cost:.6f}")
        
    except Exception as e:
        print(f"\n❌ Error terminating instance: {str(e)}")
        print("You may need to terminate it manually in AWS console")


if __name__ == "__main__":
    terminate_test_instance()