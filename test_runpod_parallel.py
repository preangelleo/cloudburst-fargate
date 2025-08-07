#!/usr/bin/env python3
"""
Test parallel batch processing with 40 scenes from RunPod failed task
"""

import os
import time
from instant_instance_operation_v2 import execute_parallel_batches

def test_runpod_scenes():
    """Test with real 40 scenes from RunPod"""
    
    # Base path on RunPod
    base_path = "/workspace/Animation/web_user/2fc4c750-c2b0-402f-bf06-6f00a4f57049/educational_story/web_1754496070276_811savu7n"
    
    # Build scene list for all 40 scenes
    scenes = []
    for i in range(1, 41):  # 1 to 40
        scene_num = f"{i:03d}"
        scene = {
            "scene_name": f"scene_{scene_num}_chinese",
            "input_image": f"{base_path}/images/scene_{scene_num}_chinese.png",
            "input_audio": f"{base_path}/audio/scene_{scene_num}_chinese.mp3",
            "subtitle": f"{base_path}/audio/scene_{scene_num}_chinese.srt"
        }
        scenes.append(scene)
    
    print(f"🎬 Processing {len(scenes)} scenes from RunPod task")
    print("=" * 60)
    
    # Test different configurations
    test_configs = [
        (10, 4, 5, "Standard: 4 instances × 10 scenes"),
    ]
    
    for scenes_per_batch, max_instances, min_scenes, description in test_configs:
        print(f"\n📊 Test: {description}")
        print(f"   Parameters: batch={scenes_per_batch}, max={max_instances}, min={min_scenes}")
        
        # Calculate expected distribution
        from instant_instance_operation_v2 import calculate_optimal_batch_distribution
        distribution = calculate_optimal_batch_distribution(
            total_scenes=len(scenes),
            scenes_per_batch=scenes_per_batch,
            max_parallel_instances=max_instances,
            min_scenes_per_batch=min_scenes
        )
        
        print(f"   Expected: {distribution['num_instances']} instances")
        print(f"   Distribution: {distribution['batch_distribution']}")
        print(f"   Strategy: {distribution['strategy']}")
        
        # Uncomment to actually run the test
        result = execute_parallel_batches(
            scenes=scenes,
            scenes_per_batch=scenes_per_batch,
            language="chinese",
            enable_zoom=True,
            max_parallel_instances=max_instances,
            min_scenes_per_batch=min_scenes
        )
        
        print(f"   ✅ Completed: {result['successful_scenes']}/{result['total_scenes']} scenes")
        print(f"   💰 Cost: ${result['total_cost_usd']:.4f}")
        print(f"   ⏱️  Time: {result['parallel_time']:.1f}s")
        print(f"   🚀 Speedup: {result['efficiency']['speedup_factor']:.1f}x")
    
    print("\n" + "=" * 60)
    
    # Recommended configuration for production
    print("\n🎯 Recommended for 40 scenes:")
    print("   execute_parallel_batches(")
    print("       scenes=scenes,")
    print("       scenes_per_batch=10,      # Balanced workload")
    print("       max_parallel_instances=4,  # 4 instances × 10 scenes")
    print("       min_scenes_per_batch=5,    # Minimum efficiency")
    print("       language='chinese'")
    print("   )")
    
    # Also test with local file paths (for running from Mac)
    print("\n📁 For local testing, update paths to:")
    print("   Copy files from RunPod to local machine first:")
    print("   scp -P 22113 -r root@69.30.85.46:/workspace/Animation/web_user/.../web_1754496070276_811savu7n ./test_scenes/")

if __name__ == "__main__":
    test_runpod_scenes()