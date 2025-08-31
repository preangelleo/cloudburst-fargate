#!/usr/bin/env python3
"""
CloudBurst Fargate Demo - Shows package usage after installation
"""

from cloudburst_fargate import FargateOperationV1, __version__

def demo():
    print(f"🚀 CloudBurst Fargate Demo v{__version__}")
    print("=" * 50)
    
    # Show available configuration options
    print("\n📊 Available CPU Configurations:")
    configs = [
        (5, "Economy: 1 vCPU, 2GB RAM (~$0.044/hour)"),
        (1, "Standard: 2 vCPU, 4GB RAM (~$0.088/hour) [Default]"),
        (2, "High Performance: 4 vCPU, 8GB RAM (~$0.175/hour)"),
        (3, "Ultra Performance: 8 vCPU, 16GB RAM (~$0.351/hour)"),
        (4, "Maximum: 16 vCPU, 32GB RAM (~$0.702/hour)")
    ]
    
    for priority, desc in configs:
        print(f"   Config {priority}: {desc}")
    
    # Initialize processor
    print("\n🔧 Initializing FargateOperationV1...")
    processor = FargateOperationV1(config_priority=1)
    print("✅ Processor initialized successfully!")
    
    # Show example scene structure
    print("\n📝 Example Scene Structure:")
    example_scene = {
        'scene_name': 'demo_scene_001',
        'image_path': '/path/to/image.png',
        'audio_path': '/path/to/audio.mp3',
        'subtitle_path': '/path/to/subtitle.srt'  # Optional
    }
    
    import json
    print(json.dumps(example_scene, indent=2))
    
    # Show parallel processing example
    print("\n⚡ Parallel Processing Example:")
    print("""
from cloudburst_fargate.fargate_operation import execute_parallel_batches

# Process 8 scenes across 4 parallel tasks
result = execute_parallel_batches(
    scenes=your_scenes,
    scenes_per_batch=2,       # 2 scenes per container
    max_parallel_tasks=4,     # 4 concurrent containers
    language='english',
    enable_zoom=True,
    config_priority=1,
    saving_dir='./output'
)

# Result includes:
# - Downloaded files
# - Processing efficiency metrics
# - Total cost breakdown
# - Speedup factor
""")
    
    # Show monitoring capabilities
    print("\n📋 Task Monitoring:")
    running_tasks = processor.list_running_tasks(filter_animagent_only=True)
    print(f"Currently running tasks: {len(running_tasks)}")
    
    if running_tasks:
        for task in running_tasks[:3]:  # Show first 3
            print(f"  - Task: {task['task_arn'][-12:]}")
            print(f"    Status: {task['status']}")
            print(f"    Started: {task.get('started_at', 'N/A')}")
    
    print("\n✨ CloudBurst Fargate is ready for production use!")
    print("📚 Documentation: https://github.com/preangelleo/cloudburst-fargate")
    print("📧 Author: Leo Wang (me@leowang.net)")

if __name__ == "__main__":
    demo()