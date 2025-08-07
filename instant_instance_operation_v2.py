#!/usr/bin/env python3
"""
Instant Instance Operation v2.0 - Enhanced Core Function
Rapidly create AWS instance, deploy Docker image, process batch scenes with effects, and cleanup

Enhanced Features:
- Batch scene processing
- Zoom effects support  
- Flexible subtitle handling
- Scene folder scanning
- Performance optimized batch operations
"""

import boto3
import requests
import base64
import time
import os
import glob
import json
from datetime import datetime
from typing import Dict, Optional, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Using environment variables directly.")

class InstantInstanceOperationV2:
    def __init__(self, config_priority=1):
        # Load configuration from environment variables
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.ec2_client = boto3.client('ec2', region_name=aws_region)
        
        # Instance Configuration Priority List (1-3)
        self.instance_configs = [
            {
                "priority": 1,
                "instance_type": "c5.2xlarge",
                "name": "CPU_HIGH_PERFORMANCE",
                "description": "Compute optimized - 8 vCPU, 16GB RAM (quota-friendly)",
                "category": "CPU-Optimized",
                "expected_performance": "Good CPU performance",
                "cost_efficiency": "Medium",
                "fallback_reason": "Multi-core processing + quota compatibility"
            },
            {
                "priority": 2,
                "instance_type": "m5.xlarge", 
                "name": "MEMORY_OPTIMIZED", 
                "description": "Memory optimized - 4 vCPU, 16GB RAM (quota-friendly)",
                "category": "Memory-Optimized",
                "expected_performance": "Balanced performance",
                "cost_efficiency": "Best",
                "fallback_reason": "Cost-effective + quota compatibility"
            },
            {
                "priority": 3,
                "instance_type": "g4dn.xlarge",
                "name": "GPU_NVIDIA_T4",
                "description": "NVIDIA T4 - 4 vCPU, 16GB RAM, 16GB GPU (quota-friendly)",
                "category": "GPU-Optimized",
                "expected_performance": "GPU acceleration with smaller footprint",
                "cost_efficiency": "High",
                "fallback_reason": "GPU encoding + quota compatibility"
            }
        ]
        
        # Select configuration based on priority (1-3)
        if 1 <= config_priority <= 3:
            self.current_config = self.instance_configs[config_priority - 1]
            self.instance_type = self.current_config["instance_type"]
            self.config_name = self.current_config["name"]
            self.config_priority = config_priority
        else:
            # Default to priority 1
            self.current_config = self.instance_configs[0]
            self.instance_type = self.current_config["instance_type"]
            self.config_name = self.current_config["name"] 
            self.config_priority = 1
        
        # AWS Configuration
        self.docker_image = os.getenv('DOCKER_IMAGE', 'betashow/video-generation-api:latest')
        self.ami_id = os.getenv('AWS_AMI_ID')
        self.key_name = os.getenv('AWS_KEY_PAIR_NAME')
        
        # Parse security group IDs (comma-separated)
        security_groups_str = os.getenv('AWS_SECURITY_GROUP_ID', '')
        self.security_group_ids = [sg.strip() for sg in security_groups_str.split(',') if sg.strip()]
        
        self.subnet_id = os.getenv('AWS_SUBNET_ID')
        
        # API Configuration
        self.api_timeout_minutes = int(os.getenv('API_TIMEOUT_MINUTES', '15'))  # Longer for batch
        self.api_request_timeout = int(os.getenv('API_REQUEST_TIMEOUT_SECONDS', '300'))  # 5 min per video
        
        # Optional authentication key
        self.auth_key = os.getenv('VIDEO_API_AUTH_KEY')
        
        # Results directory
        self.results_dir = os.getenv('RESULTS_DIR', '/tmp/instant_test_results')
        
        # Create results directory if it doesn't exist
        os.makedirs(self.results_dir, exist_ok=True)
        print(f"📁 Using results directory: {self.results_dir}")
        
        # Validate required configuration
        self._validate_configuration()
        
        # Performance tracking
        self.start_time = None
        self.timing_log = []
        self.batch_results = []
        
        # Cost tracking
        self.instance_start_time = None
        self.instance_hourly_cost = None
    
    def _validate_configuration(self):
        """Validate that required configuration is present"""
        required_configs = {
            'AWS_AMI_ID': self.ami_id,
            'AWS_KEY_PAIR_NAME': self.key_name,
            'AWS_SECURITY_GROUP_ID': self.security_group_ids,
            'AWS_SUBNET_ID': self.subnet_id
        }
        
        missing_configs = []
        for config_name, config_value in required_configs.items():
            if not config_value:
                missing_configs.append(config_name)
        
        if missing_configs:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_configs)}\\n"
                f"Please check your .env file or set these environment variables.\\n"
                f"See .env.example for required configuration format."
            )
        
    def log_timing(self, event: str):
        """Log timing for performance analysis"""
        if self.start_time is None:
            self.start_time = time.time()
            
        elapsed = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.timing_log.append(f"[{timestamp}] +{elapsed:6.2f}s - {event}")
        print(f"⏱️  [{timestamp}] +{elapsed:6.2f}s - {event}")
    
    def get_instance_pricing(self) -> float:
        """Get hourly pricing for the instance type using AWS Pricing API"""
        try:
            # AWS Pricing API is only available in us-east-1
            pricing_client = boto3.client('pricing', region_name='us-east-1')
            
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': self.instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': 'US East (N. Virginia)'}  # us-east-1
                ]
            )
            
            if response['PriceList']:
                price_item = json.loads(response['PriceList'][0])
                terms = price_item['terms']['OnDemand']
                for term_key in terms:
                    price_dimensions = terms[term_key]['priceDimensions']
                    for dimension_key in price_dimensions:
                        price_per_hour = float(price_dimensions[dimension_key]['pricePerUnit']['USD'])
                        return price_per_hour
            
            # Fallback to hardcoded prices if API fails
            pricing_fallback = {
                't3.micro': 0.0104,
                't3.small': 0.0208,
                't3.medium': 0.0416,
                't3.large': 0.0832,
                't3.xlarge': 0.1664,
                't3.2xlarge': 0.3328,
                'c5.large': 0.085,
                'c5.xlarge': 0.17,
                'm5.large': 0.096,
                'm5.xlarge': 0.192
            }
            
            return pricing_fallback.get(self.instance_type, 0.10)  # Default fallback
            
        except Exception as e:
            self.log_timing(f"Failed to get pricing via API: {str(e)}")
            # Fallback pricing for common instance types
            pricing_fallback = {
                't3.micro': 0.0104,
                't3.small': 0.0208, 
                't3.medium': 0.0416,
                't3.large': 0.0832,
                't3.xlarge': 0.1664,
                't3.2xlarge': 0.3328
            }
            return pricing_fallback.get(self.instance_type, 0.10)  # Default fallback
    
    def calculate_cost(self, runtime_seconds: float) -> Dict:
        """Calculate actual cost based on runtime"""
        if not self.instance_hourly_cost:
            self.instance_hourly_cost = self.get_instance_pricing()
        
        runtime_hours = runtime_seconds / 3600
        runtime_minutes = runtime_seconds / 60
        total_cost = runtime_hours * self.instance_hourly_cost
        
        return {
            "hourly_rate_usd": self.instance_hourly_cost,
            "runtime_seconds": runtime_seconds,
            "runtime_minutes": runtime_minutes,
            "runtime_hours": runtime_hours,
            "total_cost_usd": round(total_cost, 6),
            "cost_breakdown": {
                "instance_type": self.instance_type,
                "rate_per_hour": f"${self.instance_hourly_cost:.4f}",
                "runtime": f"{runtime_seconds:.1f}s ({runtime_minutes:.2f}min)",
                "calculation": f"${self.instance_hourly_cost:.4f}/hour × {runtime_hours:.4f}hours = ${total_cost:.6f}"
            }
        }
    
    def scan_scenes_from_folder(self, folder_path: str) -> List[Dict]:
        """
        Scan a folder and automatically generate scene list
        
        Args:
            folder_path: Path to folder containing images/, audio/ subdirectories
            
        Returns:
            List of scene dictionaries with image, audio, subtitle paths
        """
        scenes = []
        
        # Look for scene files in standard pattern: scene_XXX.*
        images_dir = os.path.join(folder_path, "images")
        audio_dir = os.path.join(folder_path, "audio")
        
        if not os.path.exists(images_dir) or not os.path.exists(audio_dir):
            raise ValueError(f"Missing images/ or audio/ directories in {folder_path}")
        
        # Find image files and match with audio/subtitle
        image_pattern = os.path.join(images_dir, "scene_*.png")
        image_files = sorted(glob.glob(image_pattern))
        
        for image_file in image_files:
            # Extract scene number from filename
            filename = os.path.basename(image_file)
            scene_name = filename.replace('.png', '')
            
            # Find corresponding audio and subtitle files
            audio_file = os.path.join(audio_dir, f"{scene_name}.mp3")
            subtitle_file = os.path.join(audio_dir, f"{scene_name}.srt")
            
            # Verify files exist
            if os.path.exists(audio_file):
                scene = {
                    "scene_name": scene_name,
                    "input_image": image_file,
                    "input_audio": audio_file,
                    "subtitle": subtitle_file if os.path.exists(subtitle_file) else None
                }
                scenes.append(scene)
                print(f"📽️ Found scene: {scene_name} (subtitle: {'✅' if scene['subtitle'] else '❌'})")
        
        print(f"🎬 Total scenes found: {len(scenes)}")
        return scenes
    
    def check_instance_availability(self, instance_type: str) -> Dict:
        """Check if instance type is available and get quota info"""
        try:
            # Check if instance type is available in region
            response = self.ec2_client.describe_instance_type_offerings(
                LocationType='availability-zone',
                Filters=[
                    {
                        'Name': 'instance-type',
                        'Values': [instance_type]
                    }
                ]
            )
            
            availability_zones = [offering['Location'] for offering in response.get('InstanceTypeOfferings', [])]
            is_available = len(availability_zones) > 0
            
            return {
                "available": is_available,
                "availability_zones": availability_zones,
                "instance_type": instance_type,
                "region": self.ec2_client._client_config.region_name
            }
            
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "instance_type": instance_type
            }
    
    def find_best_available_instance(self) -> Dict:
        """Find the best available instance from current config priority list"""
        self.log_timing("🔍 Checking instance availability before creation...")
        
        # Check current selected instance first
        current_check = self.check_instance_availability(self.instance_type)
        
        if current_check["available"]:
            self.log_timing(f"✅ Selected instance {self.instance_type} is available in {len(current_check['availability_zones'])} zones")
            return {
                "selected": True,
                "instance_type": self.instance_type,
                "config": self.current_config,
                "availability_check": current_check
            }
        
        # If current instance not available, try fallback options
        self.log_timing(f"❌ Selected instance {self.instance_type} not available, checking fallbacks...")
        
        # Define fallback instances (smaller, more likely to be available)
        fallback_instances = [
            {
                "instance_type": "t3.xlarge",
                "name": "FALLBACK_GENERAL",
                "description": "General purpose - 4 vCPU, 16GB RAM (high availability)",
                "category": "Fallback"
            },
            {
                "instance_type": "t3.large", 
                "name": "FALLBACK_SMALL",
                "description": "General purpose - 2 vCPU, 8GB RAM (most compatible)",
                "category": "Fallback"
            },
            {
                "instance_type": "m5.large",
                "name": "FALLBACK_MEMORY",
                "description": "Memory optimized - 2 vCPU, 8GB RAM (stable)",
                "category": "Fallback"
            }
        ]
        
        for fallback in fallback_instances:
            check = self.check_instance_availability(fallback["instance_type"])
            if check["available"]:
                self.log_timing(f"✅ Fallback instance {fallback['instance_type']} is available")
                
                # Update current configuration to use fallback
                fallback_config = {**self.current_config, **fallback}
                fallback_config["original_instance_type"] = self.instance_type
                fallback_config["fallback_used"] = True
                
                return {
                    "selected": True,
                    "instance_type": fallback["instance_type"],
                    "config": fallback_config,
                    "availability_check": check,
                    "fallback_from": self.instance_type
                }
        
        # No instances available
        self.log_timing("❌ No suitable instances available in current region")
        return {
            "selected": False,
            "error": "No available instances found",
            "checked_instances": [self.instance_type] + [f["instance_type"] for f in fallback_instances]
        }

    def create_instance(self) -> str:
        """Create and launch AWS EC2 instance with smart instance selection"""
        self.log_timing("Starting smart AWS instance creation")
        
        # 🆕 Smart instance selection
        availability_result = self.find_best_available_instance()
        
        if not availability_result["selected"]:
            error_msg = f"No available instances found. Checked: {availability_result.get('checked_instances', [])}"
            self.log_timing(error_msg)
            raise Exception(error_msg)
        
        # Use selected instance type (may be fallback)
        selected_instance_type = availability_result["instance_type"]
        selected_config = availability_result["config"]
        
        if availability_result.get("fallback_from"):
            self.log_timing(f"🔄 Using fallback: {selected_instance_type} (originally requested: {availability_result['fallback_from']})")
            # Update instance configuration
            self.instance_type = selected_instance_type
            self.current_config = selected_config
        
        # Get pricing information before starting instance
        self.instance_hourly_cost = self.get_instance_pricing()
        self.log_timing(f"Instance pricing: ${self.instance_hourly_cost:.4f}/hour ({self.instance_type})")
        
        # Record instance start time for cost calculation
        self.instance_start_time = time.time()
        
        user_data_script = f'''#!/bin/bash
# Update system
apt-get update -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get install -y ca-certificates curl gnupg lsb-release
    mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Pull Docker image immediately
echo "Pulling Docker image: {self.docker_image}"
docker pull {self.docker_image}

# Create ready marker
echo "Instance ready at $(date)" > /tmp/instance-ready

# Start the container with increased memory limits for batch processing
echo "Starting video generation API container..."
docker run -d --name video-api -p 5000:5000 --memory=8g {self.docker_image}

# Wait for API to be ready
echo "Waiting for API to start..."
sleep 20

# Health check loop with better error handling
for i in {{1..50}}; do
    if curl -f http://localhost:5000/health &>/dev/null; then
        echo "API is ready!" > /tmp/api-ready
        break
    fi
    echo "Waiting for API... attempt $i/50"
    sleep 3
done

# Final status check
if curl -f http://localhost:5000/health &>/dev/null; then
    echo "✅ API startup successful at $(date)"
else
    echo "❌ API startup failed at $(date)"
    docker logs video-api > /tmp/api-logs 2>&1
fi

echo "Startup completed at $(date)"
'''
        
        # 🆕 Try to create instance with automatic fallback on quota/capacity errors
        max_attempts = 3
        attempted_instances = []
        
        for attempt in range(max_attempts):
            try:
                self.log_timing(f"🚀 Attempting to create instance: {self.instance_type} (attempt {attempt + 1}/{max_attempts})")
                
                response = self.ec2_client.run_instances(
                    ImageId=self.ami_id,
                    MinCount=1,
                    MaxCount=1,
                    InstanceType=self.instance_type,
                    KeyName=self.key_name,
                    SecurityGroupIds=self.security_group_ids,
                    SubnetId=self.subnet_id,
                    UserData=user_data_script,
                    TagSpecifications=[
                        {
                            'ResourceType': 'instance',
                            'Tags': [
                                {'Key': 'Name', 'Value': f'instant-video-batch-{int(time.time())}'},
                                {'Key': 'Purpose', 'Value': 'Instant Batch Video Processing'},
                                {'Key': 'AutoTerminate', 'Value': 'true'}
                            ]
                        }
                    ]
                )
                
                instance_id = response['Instances'][0]['InstanceId']
                self.log_timing(f"✅ Instance created successfully: {instance_id}")
                return instance_id
                
            except Exception as e:
                attempted_instances.append(self.instance_type)
                error_str = str(e)
                
                # Check if it's a quota/capacity error that we can fallback from
                if any(error_type in error_str for error_type in [
                    'VcpuLimitExceeded', 'InsufficientInstanceCapacity', 
                    'InstanceLimitExceeded', 'Unsupported'
                ]):
                    self.log_timing(f"❌ {self.instance_type} failed with quota/capacity error: {error_str}")
                    
                    # Try fallback instances
                    fallback_options = [
                        ("t3.xlarge", "General purpose - 4 vCPU, 16GB RAM"),
                        ("t3.large", "General purpose - 2 vCPU, 8GB RAM"), 
                        ("m5.large", "Memory optimized - 2 vCPU, 8GB RAM")
                    ]
                    
                    fallback_found = False
                    for fallback_type, fallback_desc in fallback_options:
                        if fallback_type not in attempted_instances:
                            self.log_timing(f"🔄 Trying fallback: {fallback_type} ({fallback_desc})")
                            
                            # Update instance configuration to fallback
                            original_type = self.instance_type
                            self.instance_type = fallback_type
                            
                            # Update pricing for fallback
                            self.instance_hourly_cost = self.get_instance_pricing()
                            self.log_timing(f"💰 Fallback pricing: ${self.instance_hourly_cost:.4f}/hour ({fallback_type})")
                            
                            # Update current config
                            self.current_config = {
                                **self.current_config,
                                "instance_type": fallback_type,
                                "description": f"{fallback_desc} (fallback from {original_type})",
                                "fallback_used": True,
                                "original_instance_type": original_type
                            }
                            
                            fallback_found = True
                            break
                    
                    if not fallback_found:
                        self.log_timing(f"❌ No more fallback options available")
                        raise Exception(f"All instance types failed. Tried: {attempted_instances + [self.instance_type]}")
                        
                else:
                    # Non-quota error, don't try fallback
                    self.log_timing(f"❌ Instance creation failed with non-quota error: {error_str}")
                    raise
        
        # If we get here, all attempts failed
        raise Exception(f"Failed to create instance after {max_attempts} attempts. Tried: {attempted_instances}")
    
    def wait_for_instance_ready(self, instance_id: str) -> str:
        """Wait for instance to be running and get public IP"""
        self.log_timing("Waiting for instance to be running...")
        
        waiter = self.ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id], WaiterConfig={'Delay': 5, 'MaxAttempts': 24})
        
        response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        
        self.log_timing(f"Instance running at IP: {public_ip}")
        return public_ip
    
    def wait_for_api_ready(self, public_ip: str) -> bool:
        """Wait for Docker container and API to be ready"""
        self.log_timing("Waiting for Docker API to be ready...")
        
        api_url = f"http://{public_ip}:5000"
        max_attempts = self.api_timeout_minutes * 12  # Convert minutes to 5-second intervals
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{api_url}/health", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        self.log_timing("Docker API is ready and healthy")
                        return True
            except:
                pass
            
            if attempt % 10 == 0:
                self.log_timing(f"Still waiting for API... attempt {attempt + 1}/{max_attempts}")
            time.sleep(5)
        
        self.log_timing("API readiness check failed")
        return False
    
    def encode_file_to_base64(self, file_path: str) -> str:
        """Encode file to base64"""
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    
    def process_single_scene(self, public_ip: str, scene: Dict, language: str = "chinese", 
                           enable_zoom: bool = True, enable_subtitles: bool = True,
                           watermark_path: str = None, is_portrait: bool = False) -> Optional[Dict]:
        """
        Process a single scene with the new unified API endpoint
        
        Args:
            public_ip: EC2 instance public IP
            scene: Scene dictionary with input files
            language: Language setting
            enable_zoom: Enable zoom effects
            enable_subtitles: Whether to add subtitles
            watermark_path: Path to watermark image file (optional)
            is_portrait: Whether video is in portrait mode
        
        Returns:
            Dict with processing result or None if failed
            public_ip: API server IP
            scene: Scene dictionary with input_image, input_audio, subtitle
            language: Language setting (chinese/english)
            enable_zoom: Enable zoom in/out effects
            enable_subtitles: Enable subtitle addition
            
        Returns:
            Dict with scene results or None if failed
        """
        scene_name = scene.get('scene_name', 'unknown')
        self.log_timing(f"Processing scene: {scene_name}")
        
        # Encode files
        try:
            image_b64 = self.encode_file_to_base64(scene['input_image'])
            audio_b64 = self.encode_file_to_base64(scene['input_audio'])
            
            # Handle subtitle (optional)
            subtitle_b64 = None
            has_subtitle = scene.get('subtitle') and os.path.exists(scene['subtitle'])
            if has_subtitle and enable_subtitles:
                subtitle_b64 = self.encode_file_to_base64(scene['subtitle'])
                self.log_timing(f"Scene {scene_name}: Files encoded (with subtitles)")
            else:
                self.log_timing(f"Scene {scene_name}: Files encoded (no subtitles)")
                
        except Exception as e:
            self.log_timing(f"Scene {scene_name}: File encoding failed - {str(e)}")
            return None
        
        # Prepare request for unified API endpoint
        api_url = f"http://{public_ip}:5000"
        api_endpoint = f"{api_url}/create_video_onestep"
        
        request_data = {
            "input_image": image_b64,
            "input_audio": audio_b64,
            "language": language,
            "background_box": True,
            "background_opacity": 0.7,
            "output_filename": f"{scene_name}_{datetime.now().strftime('%H%M%S')}.mp4",
            "is_portrait": is_portrait
        }
        
        # Add effects if enabled
        if enable_zoom:
            request_data["effects"] = ["zoom_in", "zoom_out"]
            
        # Add subtitles if available (using new parameter name)
        if subtitle_b64:
            request_data["subtitle"] = subtitle_b64  # Changed from subtitle_path
            self.log_timing(f"Scene {scene_name}: Adding subtitle to request (length: {len(subtitle_b64)} chars)")
            
        # Add watermark if provided
        if watermark_path and os.path.exists(watermark_path):
            try:
                watermark_b64 = self.encode_file_to_base64(watermark_path)
                request_data["watermark"] = watermark_b64
                self.log_timing(f"Scene {scene_name}: Adding watermark to request")
            except Exception as e:
                self.log_timing(f"Scene {scene_name}: Failed to encode watermark - {str(e)}")
        
        headers = {"Content-Type": "application/json"}
        
        # Add authentication header if auth key is provided
        if self.auth_key:
            headers["X-Authentication-Key"] = self.auth_key
        
        # Determine expected scenario for logging
        scenario = "baseline"
        if enable_zoom and subtitle_b64:
            scenario = "full_featured"
        elif enable_zoom:
            scenario = "effects_only"
        elif subtitle_b64:
            scenario = "subtitles_only"
            
        self.log_timing(f"Scene {scene_name}: Using unified API endpoint (expected scenario: {scenario})")
        
        # Debug: Log request details
        self.log_timing(f"Scene {scene_name}: Request has effects: {request_data.get('effects', [])} (enable_zoom={enable_zoom})")
        self.log_timing(f"Scene {scene_name}: Request has subtitle: {'subtitle' in request_data} (length={len(request_data.get('subtitle', ''))} chars)")
        self.log_timing(f"Scene {scene_name}: Request language: {request_data.get('language')}")
        
        # Debug: Save request data for inspection
        # Use same priority as results: 1) saving_dir 2) RESULTS_DIR 3) default
        debug_base_dir = self.results_dir  # This already follows the 3-tier priority
        debug_dir = os.path.join(debug_base_dir, "debug_logs")
        os.makedirs(debug_dir, exist_ok=True)
        debug_file = os.path.join(debug_dir, f"debug_request_{scene_name}.json")
        with open(debug_file, 'w') as f:
            debug_data = request_data.copy()
            debug_data['input_image'] = f"[BASE64: {len(request_data['input_image'])} chars]"
            debug_data['input_audio'] = f"[BASE64: {len(request_data['input_audio'])} chars]"
            if 'subtitle' in debug_data:
                debug_data['subtitle'] = f"[BASE64: {len(request_data['subtitle'])} chars]"
            json.dump(debug_data, f, indent=2)
        self.log_timing(f"Scene {scene_name}: Debug request saved to {debug_file}")
        
        # Make request
        try:
            self.log_timing(f"Scene {scene_name}: Sending request to /create_video_onestep...")
            start_time = time.time()
            
            response = requests.post(api_endpoint, 
                                   json=request_data, headers=headers, 
                                   timeout=self.api_request_timeout)
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                file_id = data.get('file_id')
                file_size = data.get('size', 0)
                detected_scenario = data.get('scenario', 'unknown')
                
                self.log_timing(f"Scene {scene_name}: Completed - {file_id} ({file_size/1024/1024:.2f}MB) in {processing_time:.1f}s")
                self.log_timing(f"Scene {scene_name}: API detected scenario: {detected_scenario}")
                
                # Debug: Log mismatch
                if detected_scenario != scenario:
                    self.log_timing(f"⚠️  Scene {scene_name}: Scenario mismatch! Expected '{scenario}' but API detected '{detected_scenario}'")
                
                return {
                    "scene_name": scene_name,
                    "success": True,
                    "file_id": file_id,
                    "download_url": f"{api_url}/download/{file_id}",
                    "file_size": file_size,
                    "processing_time": processing_time,
                    "has_subtitle": subtitle_b64 is not None,
                    "has_zoom": enable_zoom,
                    "scenario": detected_scenario
                }
            else:
                self.log_timing(f"Scene {scene_name}: Generation failed - {response.status_code} - {response.text}")
                return {
                    "scene_name": scene_name,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "processing_time": processing_time
                }
                
        except Exception as e:
            self.log_timing(f"Scene {scene_name}: Request failed - {str(e)}")
            return {
                "scene_name": scene_name,
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    def terminate_instance(self, instance_id: str):
        """Terminate the AWS instance"""
        self.log_timing(f"Terminating instance: {instance_id}")
        
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            self.log_timing("Instance termination initiated")
        except Exception as e:
            self.log_timing(f"Instance termination failed: {str(e)}")
    
    def execute_batch(self, scenes: List[Dict], language: str = "chinese", 
                          enable_zoom: bool = True, auto_terminate: bool = False,
                          watermark_path: str = None, is_portrait: bool = False,
                          saving_dir: str = None) -> Dict:
        """
        Main function: Execute batch scene processing
        
        ⚠️ IMPORTANT DOWNLOAD BEHAVIOR:
        - auto_terminate=True: Videos are processed → Files downloaded automatically → Instance terminated
        - auto_terminate=False: Videos are processed → Instance kept alive → You must call download_batch_results()
        
        Args:
            scenes: List of scene dictionaries with 'scene_name', 'input_image', 'input_audio', 'subtitle' (optional)
            language: Language setting (chinese/english)
            enable_zoom: Enable zoom effects for all scenes
            auto_terminate: Whether to auto-download and terminate after processing (default: False)
                          True = Process → Download → Terminate (automatic)
                          False = Process → Keep alive (manual download required)
            watermark_path: Path to watermark image file (optional)
            is_portrait: Whether video is in portrait mode (default: False)
            saving_dir: Directory to save downloaded files (optional). Priority:
                       1. User-provided saving_dir
                       2. RESULTS_DIR from environment/.env
                       3. Default: ./cloudburst_results/
            
        Returns:
            Dict with batch processing results:
            - success: bool
            - successful_scenes: int
            - cost_usd: float (processing cost)
            - final_cost_usd: float (total cost including download, only if auto_terminate=True)
            - batch_results: list of scene results
            - downloaded_files: list of paths (only if auto_terminate=True)
            - output_directory: str (only if auto_terminate=True)
        """
        self.start_time = time.time()
        self.timing_log = []
        self.batch_results = []
        
        total_scenes = len(scenes)
        self.log_timing(f"=== BATCH INSTANT OPERATION START ({total_scenes} scenes) ===")
        
        instance_id = None
        result_dict = {}  # Initialize result dictionary for finally block
        try:
            # Phase 1: Create instance
            instance_id = self.create_instance()
            
            # Phase 2: Wait for instance ready
            public_ip = self.wait_for_instance_ready(instance_id)
            
            # Phase 3: Wait for API ready
            api_ready = self.wait_for_api_ready(public_ip)
            if not api_ready:
                raise Exception("API failed to become ready")
            
            # Notify about download behavior
            print("")  # Add blank line for clarity
            if auto_terminate:
                self.log_timing("📥 AUTO-DOWNLOAD ENABLED: Files will be downloaded automatically before termination")
            else:
                self.log_timing("📥 MANUAL DOWNLOAD MODE: Instance will stay alive - use download_batch_results() to download")
            print("")  # Add blank line for clarity
            
            # Phase 4: Process all scenes sequentially
            success_count = 0
            total_processing_time = 0
            total_file_size = 0
            downloaded_files = []
            
            # Prepare download directory based on saving_dir priority
            if saving_dir:
                download_dir = os.path.join(saving_dir, f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            else:
                download_dir = os.path.join(self.results_dir, f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(download_dir, exist_ok=True)
            self.log_timing(f"📥 Downloads will be saved to: {download_dir}")
            
            for i, scene in enumerate(scenes, 1):
                self.log_timing(f"=== Processing Scene {i}/{total_scenes} ===")
                
                result = self.process_single_scene(public_ip, scene, language, enable_zoom, 
                                                 enable_subtitles=True, watermark_path=watermark_path, 
                                                 is_portrait=is_portrait)
                
                if result:
                    self.batch_results.append(result)
                    
                    if result["success"]:
                        success_count += 1
                        total_processing_time += result["processing_time"]
                        total_file_size += result.get("file_size", 0)
                        
                        # IMMEDIATE DOWNLOAD: Download the video right after generation
                        try:
                            scene_name = result["scene_name"]
                            download_url = result["download_url"]
                            
                            self.log_timing(f"📥 Downloading {scene_name} immediately...")
                            response = requests.get(download_url, timeout=120)
                            
                            if response.status_code == 200:
                                filename = f"{scene_name}.mp4"
                                output_path = os.path.join(download_dir, filename)
                                
                                with open(output_path, 'wb') as f:
                                    f.write(response.content)
                                
                                file_size = len(response.content)
                                self.log_timing(f"✅ Downloaded {scene_name}: {file_size/1024/1024:.2f}MB → {output_path}")
                                downloaded_files.append(output_path)
                                result["local_path"] = output_path  # Add local path to result
                            else:
                                self.log_timing(f"⚠️ Download failed for {scene_name}: HTTP {response.status_code}")
                                
                        except Exception as e:
                            self.log_timing(f"⚠️ Download error for {scene_name}: {str(e)}")
                    
                    # Brief pause between scenes to avoid overwhelming API
                    if i < total_scenes:
                        time.sleep(2)
                else:
                    self.batch_results.append({
                        "scene_name": scene.get('scene_name', f'scene_{i}'),
                        "success": False,
                        "error": "Failed to process scene"
                    })
            
            total_time = time.time() - self.start_time
            self.log_timing(f"=== BATCH PROCESSING COMPLETED: {success_count}/{total_scenes} scenes successful in {total_time:.2f}s ===")
            
            # Calculate cost based on current runtime (downloads will add more time)
            current_runtime = time.time() - self.instance_start_time if self.instance_start_time else total_time
            cost_info = self.calculate_cost(current_runtime)
            self.log_timing(f"Current estimated cost: ${cost_info['total_cost_usd']:.6f} (runtime: {cost_info['runtime_minutes']:.2f}min)")
            
            # Show download summary
            if downloaded_files:
                self.log_timing(f"✅ Downloaded {len(downloaded_files)} videos to: {download_dir}")
            else:
                self.log_timing("⚠️ No videos were downloaded (check for errors above)")
            
            # 🚨 CRITICAL: Do NOT terminate instance yet - might need for retry downloads
            self.log_timing("⚠️  Keeping instance alive for potential retry downloads...")
            self._instance_kept_alive = True  # Set instance flag to prevent auto-termination
            
            result_dict = {
                "success": success_count > 0,
                "total_scenes": total_scenes,
                "successful_scenes": success_count,
                "failed_scenes": total_scenes - success_count,
                "total_time": total_time,
                "avg_processing_time": total_processing_time / success_count if success_count > 0 else 0,
                "total_file_size": total_file_size,
                "instance_id": instance_id,
                "public_ip": public_ip,
                "batch_results": self.batch_results,
                "timing_log": self.timing_log.copy(),
                "cost_usd": cost_info["total_cost_usd"],  # 🆕 Simple float for database storage
                "cost_info": cost_info,  # Detailed cost breakdown for display
                "config_used": self.current_config,  # Instance configuration used
                "_instance_kept_alive": True,  # Flag to indicate instance is still running
                "downloaded_files": downloaded_files,  # List of downloaded file paths
                "download_dir": download_dir,  # Directory where files were saved
                "download_count": len(downloaded_files)  # Number of files downloaded
            }
            return result_dict
            
        except Exception as e:
            total_time = time.time() - self.start_time if self.start_time else 0
            self.log_timing(f"=== BATCH PROCESSING FAILED: {str(e)} ===")
            
            result_dict = {
                "success": False,
                "error": str(e),
                "total_scenes": total_scenes,
                "successful_scenes": len([r for r in self.batch_results if r.get("success")]),
                "instance_id": instance_id,
                "total_time": total_time,
                "batch_results": self.batch_results,
                "timing_log": self.timing_log.copy(),
                "config_used": self.current_config if hasattr(self, 'current_config') else None
            }
            return result_dict
            
        finally:
            # Handle instance termination based on auto_terminate parameter
            if instance_id:
                if auto_terminate:
                    # Download files before terminating
                    # Check if we have any successful results (success_count may not be defined if early error)
                    successful_results = [r for r in self.batch_results if r.get("success")]
                    if successful_results:
                        self.log_timing("Auto-downloading results before termination...")
                        
                        # Use 3-tier priority for output directory
                        if saving_dir:
                            # Priority 1: User-provided directory
                            base_dir = saving_dir
                        elif os.getenv('RESULTS_DIR'):
                            # Priority 2: RESULTS_DIR from environment
                            base_dir = os.getenv('RESULTS_DIR')
                        else:
                            # Priority 3: Default fallback
                            base_dir = os.path.join(os.getcwd(), "cloudburst_results")
                        
                        output_dir = os.path.join(base_dir, f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                        download_result = self.download_batch_results(self.batch_results, output_dir, instance_id, terminate_after=True)
                        
                        # Update the return result with download info
                        result_dict["downloaded_files"] = download_result.get("downloaded_files", [])
                        result_dict["download_count"] = download_result.get("download_count", 0)
                        result_dict["final_cost_usd"] = download_result.get("final_cost_usd", result_dict.get("cost_usd", 0.0))
                        result_dict["output_directory"] = output_dir
                        
                        self.log_timing(f"Downloaded {download_result['download_count']} files to: {output_dir}")
                    else:
                        # No successful results, just terminate
                        self.log_timing("No successful results to download, terminating instance")
                        self.terminate_instance(instance_id)
                elif not (hasattr(self, '_instance_kept_alive') and self._instance_kept_alive):
                    # Only terminate on failure when auto_terminate is False
                    self.log_timing("Terminating instance due to failure or error")
                    self.terminate_instance(instance_id)
                else:
                    self.log_timing("Instance kept alive for downloads - manual termination required")
    
    def download_batch_results(self, batch_results: List[Dict], output_dir: str, instance_id: str = None, terminate_after: bool = True) -> Dict:
        """Download all successful batch results to local directory and clean up instance"""
        downloaded_files = []
        os.makedirs(output_dir, exist_ok=True)
        
        # Track download progress
        total_successful = len([r for r in batch_results if r.get("success")])
        downloaded_count = 0
        
        for result in batch_results:
            if not result.get("success"):
                continue
                
            scene_name = result["scene_name"]
            download_url = result["download_url"]
            
            try:
                self.log_timing(f"Downloading {scene_name}... ({downloaded_count + 1}/{total_successful})")
                
                response = requests.get(download_url, timeout=120)
                if response.status_code == 200:
                    filename = f"{scene_name}.mp4"
                    output_path = os.path.join(output_dir, filename)
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    self.log_timing(f"Downloaded {scene_name}: {file_size/1024/1024:.2f}MB")
                    downloaded_files.append(output_path)
                    downloaded_count += 1
                else:
                    self.log_timing(f"Download failed for {scene_name}: {response.status_code}")
                    
            except Exception as e:
                self.log_timing(f"Download error for {scene_name}: {str(e)}")
        
        # 🚨 CRITICAL FIX: Calculate final cost and terminate instance
        final_cost_usd = 0.0
        final_cost_info = None
        
        if instance_id:
            # Calculate final cost including download time
            if self.instance_start_time:
                final_runtime = time.time() - self.instance_start_time
                final_cost_info = self.calculate_cost(final_runtime)
                final_cost_usd = final_cost_info['total_cost_usd']
                self.log_timing(f"FINAL COST: ${final_cost_usd:.6f} (total runtime: {final_cost_info['runtime_minutes']:.2f}min)")
            
            # Only terminate if requested
            if terminate_after:
                if downloaded_count > 0:
                    self.log_timing(f"All downloads completed ({downloaded_count}/{total_successful}), terminating instance...")
                    self.terminate_instance(instance_id)
                else:
                    self.log_timing("No downloads successful, but terminating instance anyway...")
                    self.terminate_instance(instance_id)
            else:
                self.log_timing(f"Downloads completed ({downloaded_count}/{total_successful}), instance kept alive")
        
        return {
            "downloaded_files": downloaded_files,
            "download_count": downloaded_count,
            "total_available": total_successful,
            "final_cost_usd": final_cost_usd,  # 🆕 Simple float for database storage
            "final_cost_info": final_cost_info  # Detailed breakdown
        }


# Convenience functions for direct use
def scan_and_test_folder(folder_path: str, language: str = "chinese", 
                        enable_zoom: bool = True, config_priority: int = 1,
                        saving_dir: str = None) -> Dict:
    """
    Convenience function to scan folder and run batch processing
    
    Args:
        folder_path: Path to folder with images/ and audio/ subdirectories
        language: Language setting (chinese/english)  
        enable_zoom: Enable zoom effects
        config_priority: Instance configuration priority (1-3)
        saving_dir: Directory to save downloaded files (optional). Priority:
                   1. User-provided saving_dir
                   2. RESULTS_DIR from environment/.env
                   3. Default: ./cloudburst_results/
        
    Returns:
        Batch processing results dictionary
    """
    operation = InstantInstanceOperationV2(config_priority=config_priority)
    
    # Scan scenes from folder
    scenes = operation.scan_scenes_from_folder(folder_path)
    
    if not scenes:
        return {
            "success": False,
            "error": "No scenes found in folder",
            "total_scenes": 0,
            "config_used": operation.current_config
        }
    
    # Execute batch processing (keep instance alive for potential downloads)
    result = operation.execute_batch(scenes, language, enable_zoom, auto_terminate=False, 
                                   watermark_path=None, is_portrait=False, saving_dir=saving_dir)
    result["config_used"] = operation.current_config
    return result

def instant_batch_processing(scenes: List[Dict], language: str = "chinese", 
                      enable_zoom: bool = True, config_priority: int = 1,
                      saving_dir: str = None) -> Dict:
    """
    Convenience function for instant batch video processing
    
    Args:
        scenes: List of scene dictionaries
        language: Language setting
        enable_zoom: Enable zoom effects
        config_priority: Instance configuration priority (1-3)
        saving_dir: Directory to save downloaded files (optional). Priority:
                   1. User-provided saving_dir
                   2. RESULTS_DIR from environment/.env
                   3. Default: ./cloudburst_results/
        
    Returns:
        Batch processing results
    """
    operation = InstantInstanceOperationV2(config_priority=config_priority)
    result = operation.execute_batch(scenes, language, enable_zoom, auto_terminate=False, 
                                   watermark_path=None, is_portrait=False, saving_dir=saving_dir)
    result["config_used"] = operation.current_config
    return result


def calculate_optimal_batch_distribution(total_scenes: int, 
                                       scenes_per_batch: int = 10,
                                       max_parallel_instances: int = 10,
                                       min_scenes_per_batch: int = 5) -> Dict:
    """
    Calculate optimal distribution of scenes across instances
    
    Args:
        total_scenes: Total number of scenes to process
        scenes_per_batch: User's preferred scenes per batch
        max_parallel_instances: Maximum instances to run in parallel
        min_scenes_per_batch: Minimum scenes to justify instance startup cost
        
    Returns:
        Dict with distribution plan:
        {
            "num_instances": int,  # Actual instances to use
            "batch_distribution": List[int],  # Number of scenes per batch
            "total_batches": int,  # Same as num_instances
            "strategy": str,  # Description of strategy used
            "warnings": List[str],  # Any warnings about parameter adjustments
        }
    """
    warnings = []
    
    # Case 1: Total scenes exceeds or equals what we can handle with preferred batch size
    if total_scenes >= scenes_per_batch * max_parallel_instances:
        # Use all available instances and distribute evenly
        num_instances = max_parallel_instances
        base_scenes = total_scenes // num_instances
        remainder = total_scenes % num_instances
        
        # Create distribution: first 'remainder' instances get +1 scene
        batch_distribution = []
        for i in range(num_instances):
            batch_distribution.append(base_scenes + (1 if i < remainder else 0))
        
        strategy = f"Large batch: Using all {num_instances} instances with ~{base_scenes} scenes each"
        warnings.append(f"Overriding scenes_per_batch ({scenes_per_batch}) to handle {total_scenes} scenes")
        
        return {
            "num_instances": num_instances,
            "batch_distribution": batch_distribution,
            "total_batches": num_instances,
            "strategy": strategy,
            "warnings": warnings
        }
    
    # Case 2: Total scenes can be handled with preferred batch size
    # Start with even distribution across max instances
    num_instances = max_parallel_instances
    
    # Keep reducing instances until each has >= min_scenes_per_batch
    while num_instances > 1:
        base_scenes = total_scenes // num_instances
        remainder = total_scenes % num_instances
        
        min_batch_size = base_scenes
        
        if min_batch_size >= min_scenes_per_batch:
            # This distribution works!
            batch_distribution = []
            for i in range(num_instances):
                batch_distribution.append(base_scenes + (1 if i < remainder else 0))
            
            # Check if we're close to user's preferred scenes_per_batch
            avg_scenes = total_scenes / num_instances
            if abs(avg_scenes - scenes_per_batch) <= 2:
                strategy = f"Optimal: {num_instances} instances with ~{int(avg_scenes)} scenes each"
            else:
                strategy = f"Adjusted: {num_instances} instances to maintain minimum {min_scenes_per_batch} scenes per batch"
                if avg_scenes > scenes_per_batch:
                    warnings.append(f"Using fewer instances to ensure each has >= {min_scenes_per_batch} scenes")
            
            return {
                "num_instances": num_instances,
                "batch_distribution": batch_distribution,
                "total_batches": num_instances,
                "strategy": strategy,
                "warnings": warnings
            }
        
        # Reduce instances and try again
        num_instances -= 1
    
    # If we get here, use single instance
    return {
        "num_instances": 1,
        "batch_distribution": [total_scenes],
        "total_batches": 1,
        "strategy": f"Single instance: {total_scenes} scenes too small to parallelize efficiently",
        "warnings": [f"Using single instance as {total_scenes} scenes < {min_scenes_per_batch * 2}"]
    }


def execute_parallel_batches(scenes: List[Dict], 
                           scenes_per_batch: int = 10,
                           language: str = "chinese",
                           enable_zoom: bool = True,
                           config_priority: int = 1,
                           max_parallel_instances: int = 10,
                           min_scenes_per_batch: int = 5,
                           watermark_path: str = None,
                           is_portrait: bool = False,
                           saving_dir: str = None) -> Dict:
    """
    Execute large scene lists in parallel across multiple instances
    
    This function splits a large list of scenes into smaller batches and processes
    them simultaneously on separate AWS instances for maximum speed.
    
    Smart Distribution Logic:
    - If total scenes <= scenes_per_batch * max_parallel_instances:
      Uses requested scenes_per_batch (may use fewer instances)
    - If total scenes > scenes_per_batch * max_parallel_instances:
      Redistributes evenly across exactly max_parallel_instances
      
    Examples:
    - 50 scenes, scenes_per_batch=10, max_instances=10 → 5 instances × 10 scenes
    - 120 scenes, scenes_per_batch=10, max_instances=10 → 10 instances × 12 scenes
    - 101 scenes, scenes_per_batch=10, max_instances=10 → 10 instances (9×10 + 1×11)
    
    Args:
        scenes: List of all scene dictionaries to process
        scenes_per_batch: Preferred number of scenes per instance (default: 10)
        language: Language setting (chinese/english)
        enable_zoom: Enable zoom effects for all scenes
        config_priority: Instance configuration priority (1-3)
        max_parallel_instances: Maximum number of instances to run in parallel
        min_scenes_per_batch: Minimum scenes per instance to justify startup cost (default: 5)
        watermark_path: Optional path to watermark image
        is_portrait: Whether video is in portrait mode
        saving_dir: Directory to save downloaded files (default: ./cloudburst_results/)
        
    Returns:
        Dict with aggregated results from all batches, ordered by scene name:
        {
            "success": bool,
            "total_scenes": int,
            "successful_scenes": int,
            "failed_scenes": int,
            "total_cost_usd": float,
            "total_time": float,
            "parallel_time": float,  # Wall clock time (faster due to parallelism)
            "instances_used": int,
            "batch_results": [...],  # All scene results ordered by scene_name
            "instance_results": [...]  # Details per instance for debugging
        }
    """
    import concurrent.futures
    import threading
    
    start_time = time.time()
    total_scenes = len(scenes)
    
    # Calculate optimal batch distribution
    distribution_plan = calculate_optimal_batch_distribution(
        total_scenes=total_scenes,
        scenes_per_batch=scenes_per_batch,
        max_parallel_instances=max_parallel_instances,
        min_scenes_per_batch=min_scenes_per_batch
    )
    
    # Extract values from distribution plan
    num_instances = distribution_plan["num_instances"]
    batch_distribution = distribution_plan["batch_distribution"]
    
    print(f"🚀 Starting parallel batch processing")
    print(f"📊 Total scenes: {total_scenes}")
    print(f"🖥️  Instances to use: {num_instances}")
    print(f"📋 Strategy: {distribution_plan['strategy']}")
    
    # Print any warnings
    for warning in distribution_plan.get("warnings", []):
        print(f"⚠️  {warning}")
    
    # Split scenes into batches based on distribution plan
    scene_batches = []
    current_index = 0
    
    for batch_id, batch_size in enumerate(batch_distribution, 1):
        batch = scenes[current_index:current_index + batch_size]
        scene_batches.append({
            "batch_id": batch_id,
            "scenes": batch,
            "start_index": current_index,
            "end_index": current_index + len(batch) - 1
        })
        current_index += batch_size
    
    print(f"📊 Batch distribution: {batch_distribution}")
    
    # Thread-safe result storage
    results_lock = threading.Lock()
    instance_results = []
    active_instances = []  # Track all instance IDs for cleanup
    
    def process_batch(batch_info: Dict) -> Dict:
        """Process a single batch on its own instance"""
        batch_id = batch_info["batch_id"]
        batch_scenes = batch_info["scenes"]
        
        print(f"\n🔄 Batch {batch_id}: Processing {len(batch_scenes)} scenes")
        
        try:
            # Create instance for this batch
            operation = InstantInstanceOperationV2(config_priority=config_priority)
            
            # Execute batch (keep instance alive for downloads)
            result = operation.execute_batch(
                scenes=batch_scenes,
                language=language,
                enable_zoom=enable_zoom,
                auto_terminate=False,  # Keep alive for downloads
                watermark_path=watermark_path,
                is_portrait=is_portrait,
                saving_dir=saving_dir  # Pass saving_dir for immediate downloads
            )
            
            # Track instance ID for cleanup
            if result.get("instance_id"):
                with results_lock:
                    active_instances.append({
                        "batch_id": batch_id,
                        "instance_id": result["instance_id"],
                        "operation": operation
                    })
            
            # Add batch metadata
            result["batch_id"] = batch_id
            result["start_index"] = batch_info["start_index"]
            result["end_index"] = batch_info["end_index"]
            result["instance_type"] = operation.current_config["instance_type"]
            
            # Download results before terminating instance
            if result.get("success") and result.get("batch_results"):
                print(f"📥 Batch {batch_id}: Downloading {len(result['batch_results'])} videos...")
                
                # Create directory for this batch with priority:
                # 1. User-provided saving_dir
                # 2. RESULTS_DIR from environment/.env
                # 3. Default: ./cloudburst_results/
                if saving_dir:
                    # Priority 1: Use user-provided directory
                    base_dir = saving_dir
                elif os.getenv('RESULTS_DIR'):
                    # Priority 2: Use RESULTS_DIR from environment
                    base_dir = os.getenv('RESULTS_DIR')
                else:
                    # Priority 3: Default fallback
                    base_dir = os.path.join(os.getcwd(), "cloudburst_results")
                
                batch_dir = os.path.join(base_dir, f"batch_{batch_id}_{int(time.time())}")
                os.makedirs(batch_dir, exist_ok=True)
                
                # Check if files were already downloaded by execute_batch
                if result.get("downloaded_files") and result.get("download_dir"):
                    # Files already downloaded immediately, just terminate instance
                    print(f"✅ Batch {batch_id}: {result['download_count']} files already downloaded to {result['download_dir']}")
                    
                    # Terminate instance and get final cost
                    if result.get('instance_id'):
                        try:
                            operation.terminate_instance(result['instance_id'])
                            final_runtime = time.time() - operation.instance_start_time
                            final_cost_info = operation.calculate_cost(final_runtime)
                            result["final_cost_usd"] = final_cost_info["total_cost_usd"]
                            print(f"✅ Batch {batch_id}: Instance terminated (final cost: ${result['final_cost_usd']:.4f})")
                        except Exception as e:
                            print(f"⚠️ Batch {batch_id}: Failed to terminate instance: {str(e)}")
                else:
                    # Fallback: Download if not already done (shouldn't happen with new code)
                    download_result = operation.download_batch_results(
                        batch_results=result['batch_results'],
                        output_dir=batch_dir,
                        instance_id=result.get('instance_id')
                    )
                    
                    # Update result with download info
                    result["downloaded_files"] = download_result.get("downloaded_files", [])
                    result["download_dir"] = batch_dir
                    result["final_cost_usd"] = download_result.get("final_cost_usd", result["cost_usd"])
                    print(f"✅ Batch {batch_id}: Downloaded {len(result['downloaded_files'])} files to {batch_dir}")
            else:
                # CRITICAL: If batch failed or has no results, we must still terminate the instance
                print(f"⚠️ Batch {batch_id}: Failed or no results - terminating instance immediately")
                if result.get('instance_id'):
                    try:
                        operation.terminate_instance(result['instance_id'])
                        print(f"✅ Batch {batch_id}: Instance terminated successfully")
                    except Exception as term_error:
                        print(f"❌ Batch {batch_id}: Failed to terminate instance: {str(term_error)}")
                        # Instance will be caught by the finally block emergency cleanup
            
            with results_lock:
                instance_results.append(result)
            
            print(f"✅ Batch {batch_id}: Completed {result.get('successful_scenes', 0)}/{len(batch_scenes)} scenes")
            print(f"💰 Batch {batch_id}: Cost ${result.get('final_cost_usd', result.get('cost_usd', 0)):.4f}")
            
            return result
            
        except Exception as e:
            print(f"❌ Batch {batch_id}: Failed - {str(e)}")
            
            error_result = {
                "batch_id": batch_id,
                "success": False,
                "error": str(e),
                "start_index": batch_info["start_index"],
                "end_index": batch_info["end_index"],
                "cost_usd": 0,
                "successful_scenes": 0,
                "failed_scenes": len(batch_scenes),
                "batch_results": []
            }
            
            with results_lock:
                instance_results.append(error_result)
                
            return error_result
    
    # Track cleanup status
    cleanup_performed = False
    
    try:
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_instances) as executor:
            future_to_batch = {
                executor.submit(process_batch, batch): batch 
                for batch in scene_batches
            }
            
            # Wait for all batches to complete
            concurrent.futures.wait(future_to_batch)
        
        # Aggregate results
        all_scene_results = []
        all_downloaded_files = []
        total_cost = 0
        total_processing_time = 0
        successful_scenes = 0
        failed_scenes = 0
    
        # Sort instance results by batch_id to maintain order
        instance_results.sort(key=lambda x: x.get("batch_id", 0))
    
        for instance_result in instance_results:
            if instance_result.get("success", False):
                # Use final_cost_usd if available (includes download time)
                total_cost += instance_result.get("final_cost_usd", instance_result.get("cost_usd", 0))
                total_processing_time += instance_result.get("total_time", 0)
                successful_scenes += instance_result.get("successful_scenes", 0)
                failed_scenes += instance_result.get("failed_scenes", 0)
                
                # Collect all scene results
                for scene_result in instance_result.get("batch_results", []):
                    all_scene_results.append(scene_result)
                
                # Collect downloaded files
                for file_path in instance_result.get("downloaded_files", []):
                    all_downloaded_files.append({
                        "batch_id": instance_result.get("batch_id"),
                        "file_path": file_path,
                        "temp_dir": instance_result.get("download_dir")
                    })
            else:
                # Even failed batches count their scenes as failed
                failed_scenes += instance_result.get("failed_scenes", 0)
    
        # Sort all scene results by scene name
        all_scene_results.sort(key=lambda x: x.get("scene_name", ""))
    
        parallel_time = time.time() - start_time
    
        # Prepare final aggregated result
        final_result = {
        "success": successful_scenes > 0,  # At least some scenes succeeded
        "total_scenes": total_scenes,
        "successful_scenes": successful_scenes,
        "failed_scenes": failed_scenes,
        "total_cost_usd": round(total_cost, 6),
        "total_time": total_processing_time,  # Sum of all instance times
        "parallel_time": parallel_time,  # Actual wall clock time
        "time_saved": total_processing_time - parallel_time if num_instances > 1 else 0,
        "instances_used": num_instances,
        "scenes_per_batch": scenes_per_batch,
        "batch_results": all_scene_results,  # All scenes sorted by name
        "downloaded_files": all_downloaded_files,  # All downloaded file paths
        "instance_results": instance_results,  # Per-instance details
        "efficiency": {
            "speedup_factor": total_processing_time / parallel_time if parallel_time > 0 else 1,
            "cost_per_scene": total_cost / successful_scenes if successful_scenes > 0 else 0,
            "success_rate": successful_scenes / total_scenes if total_scenes > 0 else 0
        }
        }
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"🎬 PARALLEL BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Successful scenes: {successful_scenes}/{total_scenes}")
        print(f"❌ Failed scenes: {failed_scenes}")
        print(f"💰 Total cost: ${total_cost:.4f}")
        print(f"⏱️  Parallel time: {parallel_time:.1f}s (saved {final_result['time_saved']:.1f}s)")
        print(f"🚀 Speedup: {final_result['efficiency']['speedup_factor']:.2f}x faster")
        print(f"📥 Downloaded files: {len(all_downloaded_files)} videos")
        if all_downloaded_files:
            # Get unique directories where files were saved
            unique_dirs = set()
            for file_info in all_downloaded_files:
                temp_dir = file_info.get('temp_dir')
                if temp_dir:
                    unique_dirs.add(temp_dir)
            
            if len(unique_dirs) == 1:
                # All files in same base directory
                print(f"📁 Files saved in: {list(unique_dirs)[0]}")
            else:
                # Files in multiple directories
                print(f"📁 Files saved in {len(unique_dirs)} directories:")
                for dir_path in sorted(unique_dirs):
                    batch_count = sum(1 for f in all_downloaded_files if f.get('temp_dir') == dir_path)
                    print(f"   - {dir_path} ({batch_count} files)")
        
        # Log detailed download results if files exist
        if all_downloaded_files and len(all_downloaded_files) <= 10:  # Only show details for small batches
            print(f"\n📥 Downloaded files:")
            for file_info in all_downloaded_files:
                file_path = file_info.get('file_path', '')
                batch_id = file_info.get('batch_id', 'unknown')
                if os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"   🎬 Batch {batch_id}: {os.path.basename(file_path)} ({size_mb:.1f} MB)")
        
        print(f"{'='*60}")
        
        cleanup_performed = True
        return final_result
        
    finally:
        # CRITICAL: Emergency cleanup - terminate any instances that might still be running
        if not cleanup_performed and active_instances:
            print(f"\n⚠️  EMERGENCY CLEANUP: Terminating {len(active_instances)} instances...")
            
            for instance_info in active_instances:
                try:
                    instance_id = instance_info["instance_id"]
                    batch_id = instance_info["batch_id"]
                    operation = instance_info["operation"]
                    
                    print(f"🛑 Terminating instance for batch {batch_id} (ID: {instance_id})")
                    operation.terminate_instance(instance_id)
                    
                except Exception as e:
                    print(f"❌ Failed to terminate instance {instance_id}: {str(e)}")
                    # Try direct EC2 termination as last resort
                    try:
                        import boto3
                        ec2 = boto3.client('ec2', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
                        ec2.terminate_instances(InstanceIds=[instance_id])
                        print(f"✅ Terminated via direct EC2 API call")
                    except:
                        print(f"🚨 CRITICAL: Could not terminate instance {instance_id} - manual cleanup required!")
            
            print(f"⚠️  Emergency cleanup completed\n")