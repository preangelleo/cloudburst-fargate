#!/usr/bin/env python3
"""
Quick Start Example for CloudBurst Fargate

This example demonstrates basic usage of the CloudBurst Fargate library
for serverless video processing.
"""

from cloudburst_fargate import FargateOperationV1

def main():
    # Initialize with standard configuration (2 vCPU, 4GB RAM)
    processor = FargateOperationV1(config_priority=1)
    
    # Process a single scene
    scenes = [{
        'scene_name': 'sunset_scene',
        'image_path': 'path/to/sunset.png',  # Replace with actual path
        'audio_path': 'path/to/narration.mp3',  # Replace with actual path
        'subtitle_path': 'path/to/subtitle.srt'  # Optional
    }]
    
    # Execute batch processing
    result = processor.execute_batch(
        scenes=scenes,
        language='english',
        enable_zoom=True,
        saving_dir='./output'
    )
    
    if result['success']:
        print(f"✅ Processing completed successfully!")
        print(f"Scenes processed: {result['successful_scenes']}")
        print(f"Processing time: {result['processing_time']:.2f} seconds")
        print(f"Total cost: ${result['total_cost_usd']:.4f}")
        
        # List any running tasks
        running_tasks = processor.list_running_tasks()
        if running_tasks:
            print(f"\n📋 Running tasks: {len(running_tasks)}")
            for task in running_tasks:
                print(f"   - {task['task_arn']}: {task['status']}")
        
        print("\n🎬 Video processing complete!")
    else:
        print(f"❌ Failed to process: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()