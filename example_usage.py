#!/usr/bin/env python3
"""
Example usage of InstantInstanceOperation v2 for developers
Shows how to integrate this into your own projects with detailed structure examples
"""

import os
import json
import time
from instant_instance_operation_v2 import InstantInstanceOperationV2, scan_and_test_folder

def example_1_simple_folder_scan():
    """
    Example 1: Simplest usage - scan a folder and process all scenes
    
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
        config_priority=1                    # 1=GPU, 2=High-CPU, 3=Balanced
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
        
        # Example: Save to your database
        database_record = {
            "batch_id": f"batch_{int(time.time())}",
            "download_urls": download_urls,      # List of URLs
            "cost_usd": total_cost,             # Direct float value
            "processing_time": result["total_time"]
        }
        # your_database.save(database_record)
        
    return result


def example_2_custom_scene_list():
    """
    Example 2: Process specific scenes with custom configuration
    Use this when you have files in different locations or custom naming
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
    result = operation.execute_batch_test(
        scenes=scenes,                                      # List of scene dictionaries
        language="english",                                 # "chinese" or "english"
        enable_zoom=True                                    # Enable zoom effects
    )
    
    # RETURN STRUCTURE - Same as example_1
    
    if result["success"]:
        print(f"✅ Processed {result['successful_scenes']}/{result['total_scenes']} scenes")
        print(f"⏱️  Processing time: {result['total_time']:.1f}s")
        print(f"💰 Processing cost: ${result['cost_usd']:.6f}")
        
        # Download results to local machine
        output_dir = "/path/to/output"
        download_result = operation.download_batch_results(
            batch_results=result['batch_results'],          # Pass the batch_results from above
            output_dir=output_dir,                          # Local directory to save files
            instance_id=result['instance_id']               # Instance ID from result
        )
        
        # DOWNLOAD RESULT STRUCTURE:
        # download_result = {
        #     "download_count": 2,                          # Number of files downloaded
        #     "downloaded_files": [                         # List of local file paths
        #         "/path/to/output/intro_scene.mp4",
        #         "/path/to/output/main_scene.mp4"
        #     ],
        #     "final_cost_usd": 0.0195                     # Final cost including download time
        # }
        
        print(f"📥 Downloaded {download_result['download_count']} files")
        print(f"💰 Final cost: ${download_result['final_cost_usd']:.6f}")
    
    return result


def example_3_single_scene_test():
    """
    Example 3: Test a single scene
    Perfect for testing or processing individual files
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
    result = operation.execute_batch_test(
        scenes=[scene],                                             # List with single scene
        language="chinese",                                         # Language for subtitle rendering
        enable_zoom=True                                           # Enable zoom effects
    )
    
    if result["success"]:
        # Get the download URL for the single scene
        scene_result = result["batch_results"][0]                  # First (and only) result
        if scene_result["success"]:
            download_url = scene_result["download_url"]
            print(f"✅ Video ready: {download_url}")
            print(f"📊 Scenario detected: {scene_result['scenario']}")
            print(f"💰 Cost: ${result['cost_usd']:.6f}")
            
            # Download the video locally
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


if __name__ == "__main__":
    print("InstantInstanceOperation v2 - Usage Examples")
    print("=" * 50)
    print("\nAvailable examples:")
    print("1. Simple folder scan - Process all scenes in a folder")
    print("2. Custom scene list - Process specific files")
    print("3. Single scene test - Test with one file")
    print("4. API integration - Get URLs without downloading")
    print("5. Production ready - With error handling and reporting")
    
    # Uncomment the example you want to run:
    
    # example_1_simple_folder_scan()
    # example_2_custom_scene_list()
    example_3_single_scene_test()  # This one works with your test files
    # example_4_api_integration()
    # example_5_production_with_error_handling()
    
    print("\n✅ Example completed!")