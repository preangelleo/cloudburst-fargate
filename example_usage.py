#!/usr/bin/env python3
"""
Example usage of InstantInstanceOperation v2 for developers
Shows how to integrate this into your own projects with detailed structure examples

⚡ CRITICAL: DOWNLOAD BEHAVIOR
================================
NEW: Videos download immediately as each scene is generated!
auto_terminate=True  → Process & Download each → Terminate (files in result['downloaded_files'])
auto_terminate=False → Process & Download each → Keep alive (instance available for debugging)
Default: auto_terminate=False (keeps instance for inspection/retry)

📁 OUTPUT DIRECTORIES:
- execute_batch: Uses RESULTS_DIR from .env or /tmp/instant_test_results/
- execute_parallel_batches: Uses saving_dir parameter or ./cloudburst_results/
================================
"""

import os
import json
import time
from instant_instance_operation_v2 import InstantInstanceOperationV2, scan_and_test_folder, execute_parallel_batches

def example_1_simple_folder_scan():
    """
    Example 1: Simplest usage - scan a folder and process all scenes
    
    NOTE: scan_and_test_folder() uses auto_terminate=False by default,
    so instance stays alive for manual download or further processing!
    
    FOLDER STRUCTURE REQUIRED:
    your_scenes_folder/
    ├── images/
    │   ├── scene_001.png
    │   ├── scene_002.png
    │   └── scene_003.png
    ├── audio/
    │   ├── scene_001.mp3
    │   ├── scene_002.mp3
    │   └── scene_003.mp3
    └── subtitle/ (optional)
        ├── scene_001.srt
        ├── scene_002.srt
        └── scene_003.srt
    """
    print("Example 1: Simple Folder Scan")
    print("-" * 40)
    
    # Process all scenes in a folder
    result = scan_and_test_folder(
        folder_path="/path/to/your/scenes",  # Root folder containing images/, audio/, subtitle/
        language="chinese",                   # "chinese" or "english"
        enable_zoom=True,                    # True = effects enabled, False = no effects
        config_priority=1,                   # 1=GPU, 2=High-CPU, 3=Balanced
        saving_dir="/path/to/save/videos"    # Optional: where to save videos (uses RESULTS_DIR by default)
    )
    
    # RETURN STRUCTURE:
    # result = {
    #     "success": True,                    # bool - Overall success
    #     "cost_usd": 0.0187,                # float - Total AWS cost
    #     "total_time": 385.2,               # float - Total seconds
    #     "total_scenes": 15,                # int - Number of scenes attempted
    #     "successful_scenes": 15,           # int - Number succeeded
    #     "failed_scenes": 0,                # int - Number failed
    #     "batch_results": [                 # list - Individual results
    #         {
    #             "scene_name": "scene_001",
    #             "success": True,
    #             "download_url": "http://3.83.187.152:5000/download/uuid1",
    #             "file_size": 1450000,      # bytes
    #             "processing_time": 18.5,   # seconds
    #             "has_subtitle": True,
    #             "has_zoom": True,
    #             "scenario": "full_featured"  # baseline/subtitles_only/effects_only/full_featured
    #         },
    #         # ... more scenes
    #     ]
    # }
    
    if result["success"]:
        # Extract key data for your application
        download_urls = [scene["download_url"] for scene in result["batch_results"] if scene["success"]]
        total_cost = result["cost_usd"]
        
        print(f"✅ Generated {len(download_urls)} videos")
        print(f"💰 Total cost: ${total_cost:.6f}")
        
        # Check if files were auto-downloaded (scan_and_test_folder uses auto_terminate=True)
        if result.get('downloaded_files'):
            print(f"📥 Files auto-downloaded to: {result.get('output_directory', 'output')}")
            for file_path in result['downloaded_files']:
                print(f"   🎬 {file_path}")
        
        # Example: Save to your database
        database_record = {
            "batch_id": f"batch_{int(time.time())}",
            "download_urls": download_urls,      # List of URLs
            "local_files": result.get('downloaded_files', []),  # Local file paths if auto-downloaded
            "cost_usd": total_cost,             # Direct float value
            "processing_time": result["total_time"]
        }
        # your_database.save(database_record)
        
    return result


def example_2_custom_scene_list():
    """
    Example 2: Process specific scenes with custom configuration
    Use this when you have files in different locations or custom naming
    
    IMPORTANT DOWNLOAD BEHAVIOR:
    - auto_terminate=True: Files download immediately during processing, then instance terminates
    - auto_terminate=False: Files download immediately during processing, instance stays alive for debugging
    """
    print("\nExample 2: Custom Scene List")
    print("-" * 40)
    
    # Initialize with custom configuration
    operation = InstantInstanceOperationV2(config_priority=2)  # Use memory-optimized instance
    
    # SCENE STRUCTURE:
    # Each scene is a dictionary with these keys:
    scenes = [
        {
            "scene_name": "intro_scene",                    # Required: unique identifier
            "input_image": "/path/to/intro.png",           # Required: image file path
            "input_audio": "/path/to/intro.mp3",           # Required: audio file path  
            "subtitle": "/path/to/intro.srt"               # Optional: subtitle file path (can be None)
        },
        {
            "scene_name": "main_scene",
            "input_image": "/path/to/main.png",
            "input_audio": "/path/to/main.mp3", 
            "subtitle": None                                # No subtitle for this scene
        }
    ]
    
    # Execute batch processing
    result = operation.execute_batch(
        scenes=scenes,                                      # List of scene dictionaries
        language="english",                                 # "chinese" or "english"
        enable_zoom=True,                                   # Enable zoom effects
        auto_terminate=False                                # Keep instance alive (manual download required)
                                                           # Set to True for automatic download before termination
    )
    
    # RETURN STRUCTURE - Same as example_1
    
    if result["success"]:
        print(f"✅ Processed {result['successful_scenes']}/{result['total_scenes']} scenes")
        print(f"⏱️  Processing time: {result['total_time']:.1f}s")
        print(f"💰 Processing cost: ${result['cost_usd']:.6f}")
        
        # NEW: Files already downloaded during processing!
        print(f"📥 Downloaded {result['download_count']} files to: {result['download_dir']}")
        for file_path in result['downloaded_files']:
            print(f"  → {file_path}")
        
        # Optional: Re-download specific files if needed (rarely necessary)
        # download_result = operation.download_batch_results(
        #     batch_results=result['batch_results'],
        #     output_dir="/alternative/output/path",
        #     instance_id=result['instance_id']
        # )
        
        # When done, terminate instance if auto_terminate=False
        if not auto_terminate and result.get('instance_id'):
            operation.terminate_instance(result['instance_id'])
            print("✅ Instance terminated")
    
    return result


def example_3_single_scene_test():
    """
    Example 3: Test a single scene
    Perfect for testing or processing individual files
    
    DOWNLOAD BEHAVIOR OPTIONS:
    1. auto_terminate=True: Process → Download → Terminate (automatic)
    2. auto_terminate=False: Process → Keep alive (manual download required)
    """
    print("\nExample 3: Single Scene Test")
    print("-" * 40)
    
    # Use the test files from Temps folder
    operation = InstantInstanceOperationV2(config_priority=1)  # Use GPU instance
    
    # SINGLE SCENE STRUCTURE:
    scene = {
        "scene_name": "scene_009_chinese",                          # Unique name (no extension)
        "input_image": "/Users/lgg/coding/sumatman/runpod/Temps/scene_009_chinese.png",
        "input_audio": "/Users/lgg/coding/sumatman/runpod/Temps/scene_009_chinese.mp3",
        "subtitle": "/Users/lgg/coding/sumatman/runpod/Temps/scene_009_chinese.srt"
    }
    
    # Process single scene (pass as list with one item)
    result = operation.execute_batch(
        scenes=[scene],                                             # List with single scene
        language="chinese",                                         # Language for subtitle rendering
        enable_zoom=True,                                           # Enable zoom effects
        auto_terminate=False                                        # Keep instance alive for manual download
                                                                   # Change to True for automatic download
    )
    
    if result["success"]:
        # Get the download URL for the single scene
        scene_result = result["batch_results"][0]                  # First (and only) result
        if scene_result["success"]:
            download_url = scene_result["download_url"]
            print(f"✅ Video ready: {download_url}")
            print(f"📊 Scenario detected: {scene_result['scenario']}")
            print(f"💰 Cost: ${result['cost_usd']:.6f}")
            
            # Download the video locally (only if auto_terminate=False)
            # With auto_terminate=True, check result['downloaded_files'] instead
            output_dir = "/Users/lgg/coding/sumatman/runpod/Temps/test_results"
            download_result = operation.download_batch_results(
                batch_results=result['batch_results'],
                output_dir=output_dir,
                instance_id=result['instance_id']
            )
            
            if download_result['downloaded_files']:
                print(f"📁 Video saved to: {download_result['downloaded_files'][0]}")
    
    return result


def example_4_api_integration():
    """
    Example 4: Direct API call without file downloads
    Use this when you just need the download URLs (e.g., for web service)
    """
    print("\nExample 4: API Integration (URLs only)")
    print("-" * 40)
    
    # Initialize operation
    operation = InstantInstanceOperationV2()
    
    # Create instance
    instance_id, instance_ip = operation.create_instance()
    
    # Deploy Docker container
    operation.deploy_docker_container(instance_ip)
    
    # Wait for API to be ready
    api_url = f"http://{instance_ip}:5000"
    if operation.wait_for_api_ready(api_url):
        
        # Prepare API request data
        # API EXPECTS BASE64 ENCODED FILES:
        import base64
        
        with open("/path/to/image.png", "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        with open("/path/to/audio.mp3", "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
            
        with open("/path/to/subtitle.srt", "rb") as f:
            subtitle_b64 = base64.b64encode(f.read()).decode()
        
        # API REQUEST STRUCTURE:
        request_data = {
            "input_image": image_b64,        # Base64 encoded image
            "input_audio": audio_b64,        # Base64 encoded audio
            "subtitle": subtitle_b64,        # Base64 encoded subtitle (optional)
            "effects": ["zoom_in"],          # List of effects: zoom_in, zoom_out, pan_left, pan_right
            "language": "chinese",           # "chinese" or "english"
            "background_box": True,          # Show subtitle background
            "background_opacity": 0.7,       # Background opacity (0-1)
            "output_filename": "my_video.mp4"
        }
        
        # Call API
        response_data, _ = operation.call_api_and_download(
            api_url=api_url,
            request_data=request_data,
            output_filename=None,            # None = don't download, just get URL
            skip_download=True               # Skip download step
        )
        
        # API RESPONSE STRUCTURE:
        # response_data = {
        #     "success": True,
        #     "file_id": "uuid-here",
        #     "download_endpoint": "/download/uuid-here",
        #     "filename": "my_video.mp4",
        #     "size": 1234567,               # bytes
        #     "scenario": "full_featured"     # Detected scenario
        # }
        
        if response_data.get("success"):
            download_url = f"{api_url}{response_data['download_endpoint']}"
            print(f"✅ Video URL: {download_url}")
            print(f"📊 Scenario: {response_data['scenario']}")
            print(f"📦 Size: {response_data['size']} bytes")
    
    # Calculate cost and terminate
    total_cost = operation.calculate_running_cost()
    operation.terminate_instance()
    
    print(f"💰 Total cost: ${total_cost:.6f}")


def example_5_production_with_error_handling():
    """
    Example 5: Production-ready integration with comprehensive error handling
    """
    print("\nExample 5: Production Integration")
    print("-" * 40)
    
    # Production configuration
    scenes_folder = "/production/scenes/batch_001"
    output_folder = "/production/outputs/batch_001"
    
    try:
        # Process with error handling
        result = scan_and_test_folder(
            folder_path=scenes_folder,
            language="chinese",
            enable_zoom=True,
            config_priority=1  # Use fastest instance
        )
        
        if result["success"]:
            # PRODUCTION DATA STRUCTURE FOR YOUR SYSTEM:
            production_data = {
                "batch_id": f"prod_{int(time.time())}",
                "status": "completed",
                "statistics": {
                    "total_scenes": result["total_scenes"],
                    "successful_scenes": result["successful_scenes"],
                    "failed_scenes": result["failed_scenes"],
                    "processing_time_seconds": result["total_time"],
                    "average_time_per_scene": result["total_time"] / result["successful_scenes"] if result["successful_scenes"] > 0 else 0
                },
                "cost": {
                    "amount_usd": result["cost_usd"],              # Direct float for billing
                    "instance_type": result.get("instance_type", "unknown"),
                    "runtime_minutes": result["total_time"] / 60
                },
                "outputs": []
            }
            
            # Collect successful outputs
            for scene in result["batch_results"]:
                if scene["success"]:
                    production_data["outputs"].append({
                        "scene_name": scene["scene_name"],
                        "download_url": scene["download_url"],
                        "file_size_mb": scene["file_size"] / 1024 / 1024,
                        "has_effects": scene["has_zoom"],
                        "has_subtitles": scene["has_subtitle"],
                        "scenario": scene["scenario"],
                        "processing_time": scene["processing_time"]
                    })
            
            # Save production report
            os.makedirs(output_folder, exist_ok=True)
            report_file = f"{output_folder}/production_report.json"
            with open(report_file, 'w') as f:
                json.dump(production_data, f, indent=2)
            
            print(f"✅ Production batch completed")
            print(f"📊 Success rate: {production_data['statistics']['successful_scenes']}/{production_data['statistics']['total_scenes']}")
            print(f"💰 Total cost: ${production_data['cost']['amount_usd']:.6f}")
            print(f"📝 Report saved: {report_file}")
            
            return production_data
            
        else:
            # Handle failure
            error_data = {
                "batch_id": f"prod_failed_{int(time.time())}",
                "status": "failed",
                "error": result.get("error", "Unknown error"),
                "partial_results": len([r for r in result.get("batch_results", []) if r.get("success", False)])
            }
            
            print(f"❌ Production batch failed: {error_data['error']}")
            return error_data
            
    except Exception as e:
        # Log exception for production monitoring
        import traceback
        error_trace = traceback.format_exc()
        
        critical_error = {
            "batch_id": f"prod_error_{int(time.time())}",
            "status": "error",
            "exception": str(e),
            "traceback": error_trace
        }
        
        print(f"🚨 Critical error: {str(e)}")
        # Send to monitoring system
        # monitoring.alert("Video batch processing failed", critical_error)
        
        return critical_error


def example_6_parallel_processing():
    """
    Example 6: Process 100+ scenes in parallel across multiple instances
    Perfect for large batch jobs that need to complete quickly
    """
    print("\nExample 6: Parallel Batch Processing")
    print("-" * 40)
    
    # Simulate a large scene list (in practice, load from your source)
    scenes = []
    for i in range(1, 101):  # 100 scenes
        scenes.append({
            "scene_name": f"scene_{i:03d}",
            "input_image": f"/path/to/images/scene_{i:03d}.png",
            "input_audio": f"/path/to/audio/scene_{i:03d}.mp3",
            "subtitle": f"/path/to/subtitles/scene_{i:03d}.srt" if i % 2 == 0 else None
        })
    
    # Process 100 scenes with 10 scenes per instance (10 instances in parallel)
    result = execute_parallel_batches(
        scenes=scenes,
        scenes_per_batch=10,        # 10 scenes per instance
        language="english",
        enable_zoom=True,
        config_priority=1,          # Use fastest instances
        max_parallel_instances=10,  # Up to 10 instances at once
        saving_dir="./batch_output" # Optional: specify where to save videos
    )
    
    # RETURN STRUCTURE:
    # result = {
    #     "success": True,
    #     "total_scenes": 100,
    #     "successful_scenes": 98,
    #     "failed_scenes": 2,
    #     "total_cost_usd": 2.153400,      # Total cost across all instances
    #     "total_time": 2500.5,            # Sum of all instance processing times
    #     "parallel_time": 265.3,          # Actual wall clock time (10x faster!)
    #     "time_saved": 2235.2,            # Time saved by parallelism
    #     "instances_used": 10,
    #     "scenes_per_batch": 10,
    #     "batch_results": [...],          # All 100 scene results, sorted by scene_name
    #     "instance_results": [...],       # Details for each of the 10 instances
    #     "efficiency": {
    #         "speedup_factor": 9.42,      # Almost 10x speedup!
    #         "cost_per_scene": 0.0220,    # Average cost per scene
    #         "success_rate": 0.98         # 98% success rate
    #     }
    # }
    
    if result["success"]:
        print(f"\n📊 PARALLEL PROCESSING RESULTS:")
        print(f"✅ Completed: {result['successful_scenes']}/{result['total_scenes']} scenes")
        print(f"💰 Total cost: ${result['total_cost_usd']:.4f}")
        print(f"⏱️  Time comparison:")
        print(f"   - Sequential would take: {result['total_time']:.1f}s")
        print(f"   - Parallel actually took: {result['parallel_time']:.1f}s")
        print(f"   - Time saved: {result['time_saved']:.1f}s")
        print(f"🚀 Speedup: {result['efficiency']['speedup_factor']:.2f}x faster!")
        print(f"💵 Cost per scene: ${result['efficiency']['cost_per_scene']:.4f}")
        
        # Example: Process results for your application
        successful_videos = [
            scene for scene in result["batch_results"] 
            if scene.get("success", False)
        ]
        
        # Group by scenario type
        scenarios = {}
        for video in successful_videos:
            scenario = video.get("scenario", "unknown")
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(video["scene_name"])
        
        print(f"\n📈 Videos by scenario type:")
        for scenario, scene_names in scenarios.items():
            print(f"   {scenario}: {len(scene_names)} videos")
        
        # Save batch report
        report = {
            "batch_id": f"parallel_batch_{int(time.time())}",
            "summary": {
                "total_scenes": result["total_scenes"],
                "successful": result["successful_scenes"],
                "failed": result["failed_scenes"],
                "instances_used": result["instances_used"],
                "speedup": result["efficiency"]["speedup_factor"],
                "total_cost_usd": result["total_cost_usd"]
            },
            "performance": {
                "parallel_time_seconds": result["parallel_time"],
                "sequential_time_estimate": result["total_time"],
                "time_saved_seconds": result["time_saved"],
                "efficiency_percentage": (result["time_saved"] / result["total_time"] * 100) if result["total_time"] > 0 else 0
            },
            "videos": successful_videos
        }
        
        with open("parallel_batch_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: parallel_batch_report.json")
    
    return result


if __name__ == "__main__":
    print("InstantInstanceOperation v2 - Usage Examples")
    print("=" * 50)
    print("\n⚡ IMPORTANT: Download Behavior")
    print("   - auto_terminate=True: Automatically downloads files before terminating")
    print("   - auto_terminate=False: Keeps instance alive; manual download required")
    print("   - Default: auto_terminate=False (to prevent accidental termination)")
    print("\nAvailable examples:")
    print("1. Simple folder scan - Process all scenes in a folder")
    print("2. Custom scene list - Process specific files")
    print("3. Single scene test - Test with one file")
    print("4. API integration - Get URLs without downloading")
    print("5. Production ready - With error handling and reporting")
    print("6. Parallel processing - Process 100+ scenes across multiple instances")
    
    # Uncomment the example you want to run:
    
    # example_1_simple_folder_scan()
    # example_2_custom_scene_list()
    example_3_single_scene_test()  # This one works with your test files
    # example_4_api_integration()
    # example_5_production_with_error_handling()
    # example_6_parallel_processing()  # Process 100 scenes in parallel!
    
    print("\n✅ Example completed!")