#!/usr/bin/env python3
"""
Instant Instance Operation v2.0 - Enhanced Core Function
Rapidly create AWS instance, deploy Docker image, test batch scenes with effects, and cleanup

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
        
        # 🆕 Instance Configuration Priority List (1-3) - QUOTA-FRIENDLY VERSION
        self.instance_configs = [
            {
                "priority": 1,
                "instance_type": "c5.2xlarge",  # 🔧 Changed from 8xlarge to 2xlarge (quota-friendly)
                "name": "CPU_HIGH_PERFORMANCE",
                "description": "Compute optimized - 8 vCPU, 16GB RAM (quota-friendly)",
                "category": "CPU-Optimized",
                "expected_performance": "Good CPU performance",
                "cost_efficiency": "Medium",
                "fallback_reason": "Multi-core processing + quota compatibility"
            },
            {
                "priority": 2,
                "instance_type": "m5.xlarge",  # 🔧 Changed from 4xlarge to xlarge (quota-friendly) 
                "name": "MEMORY_OPTIMIZED", 
                "description": "Memory optimized - 4 vCPU, 16GB RAM (quota-friendly)",
                "category": "Memory-Optimized",
                "expected_performance": "Balanced performance",
                "cost_efficiency": "Best",
                "fallback_reason": "Cost-effective + quota compatibility"
            },
            {
                "priority": 3,
                "instance_type": "g4dn.xlarge",  # 🔧 Changed from 4xlarge to xlarge (quota-friendly)
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
        
        # Look for scene files in standard pattern: scene_XXX_chinese.*
        images_dir = os.path.join(folder_path, "images")
        audio_dir = os.path.join(folder_path, "audio")
        
        if not os.path.exists(images_dir) or not os.path.exists(audio_dir):
            raise ValueError(f"Missing images/ or audio/ directories in {folder_path}")
        
        # Find image files and match with audio/subtitle
        image_pattern = os.path.join(images_dir, "scene_*_chinese.png")
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
                                {'Key': 'Purpose', 'Value': 'Instant Batch Video Testing'},
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
                           enable_zoom: bool = True, enable_subtitles: bool = True) -> Optional[Dict]:
        """
        Process a single scene with the new unified API endpoint
        
        Args:
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
            "output_filename": f"{scene_name}_{datetime.now().strftime('%H%M%S')}.mp4"
        }
        
        # Add effects if enabled
        if enable_zoom:
            request_data["effects"] = ["zoom_in", "zoom_out"]
            
        # Add subtitles if available (using new parameter name)
        if subtitle_b64:
            request_data["subtitle"] = subtitle_b64  # Changed from subtitle_path
            self.log_timing(f"Scene {scene_name}: Adding subtitle to request (length: {len(subtitle_b64)} chars)")
        
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
        debug_file = f"/Users/lgg/coding/sumatman/Temps/debug_request_{scene_name}.json"
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
    
    def execute_batch_test(self, scenes: List[Dict], language: str = "chinese", 
                          enable_zoom: bool = True) -> Dict:
        """
        Main function: Execute batch scene testing
        
        Args:
            scenes: List of scene dictionaries
            language: Language setting (chinese/english)
            enable_zoom: Enable zoom effects for all scenes
            
        Returns:
            Dict with batch test results and performance metrics
        """
        self.start_time = time.time()
        self.timing_log = []
        self.batch_results = []
        
        total_scenes = len(scenes)
        self.log_timing(f"=== BATCH INSTANT OPERATION START ({total_scenes} scenes) ===")
        
        instance_id = None
        try:
            # Phase 1: Create instance
            instance_id = self.create_instance()
            
            # Phase 2: Wait for instance ready
            public_ip = self.wait_for_instance_ready(instance_id)
            
            # Phase 3: Wait for API ready
            api_ready = self.wait_for_api_ready(public_ip)
            if not api_ready:
                raise Exception("API failed to become ready")
            
            # Phase 4: Process all scenes sequentially
            success_count = 0
            total_processing_time = 0
            total_file_size = 0
            
            for i, scene in enumerate(scenes, 1):
                self.log_timing(f"=== Processing Scene {i}/{total_scenes} ===")
                
                result = self.process_single_scene(public_ip, scene, language, enable_zoom, enable_subtitles=True)
                
                if result:
                    self.batch_results.append(result)
                    
                    if result["success"]:
                        success_count += 1
                        total_processing_time += result["processing_time"]
                        total_file_size += result.get("file_size", 0)
                    
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
            self.log_timing(f"=== BATCH TEST COMPLETED: {success_count}/{total_scenes} scenes successful in {total_time:.2f}s ===")
            
            # Calculate cost based on current runtime (downloads will add more time)
            current_runtime = time.time() - self.instance_start_time if self.instance_start_time else total_time
            cost_info = self.calculate_cost(current_runtime)
            self.log_timing(f"Current estimated cost: ${cost_info['total_cost_usd']:.6f} (runtime: {cost_info['runtime_minutes']:.2f}min)")
            
            # 🚨 CRITICAL: Do NOT terminate instance yet - downloads happen outside this function
            self.log_timing("⚠️  Keeping instance alive for batch downloads...")
            self._instance_kept_alive = True  # Set instance flag to prevent auto-termination
            
            return {
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
                "_instance_kept_alive": True  # Flag to indicate instance is still running
            }
            
        except Exception as e:
            total_time = time.time() - self.start_time if self.start_time else 0
            self.log_timing(f"=== BATCH TEST FAILED: {str(e)} ===")
            
            return {
                "success": False,
                "error": str(e),
                "total_scenes": total_scenes,
                "successful_scenes": len([r for r in self.batch_results if r.get("success")]),
                "instance_id": instance_id,
                "total_time": total_time,
                "batch_results": self.batch_results,
                "timing_log": self.timing_log.copy()
            }
            
        finally:
            # 🚨 CRITICAL FIX: Only terminate instance on FAILURE, not success
            # Success case: instance stays alive for downloads
            if instance_id and not (hasattr(self, '_instance_kept_alive') and self._instance_kept_alive):
                self.log_timing("Terminating instance due to failure or error")
                self.terminate_instance(instance_id)
            elif instance_id:
                self.log_timing("Instance kept alive for downloads - manual termination required")
    
    def download_batch_results(self, batch_results: List[Dict], output_dir: str, instance_id: str = None) -> Dict:
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
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{scene_name}_{timestamp}.mp4"
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
            
            if downloaded_count > 0:
                self.log_timing(f"All downloads completed ({downloaded_count}/{total_successful}), terminating instance...")
                self.terminate_instance(instance_id)
            else:
                self.log_timing("No downloads successful, but terminating instance anyway...")
                self.terminate_instance(instance_id)
        
        return {
            "downloaded_files": downloaded_files,
            "download_count": downloaded_count,
            "total_available": total_successful,
            "final_cost_usd": final_cost_usd,  # 🆕 Simple float for database storage
            "final_cost_info": final_cost_info  # Detailed breakdown
        }


# Convenience functions for direct use
def scan_and_test_folder(folder_path: str, language: str = "chinese", 
                        enable_zoom: bool = True, config_priority: int = 1) -> Dict:
    """
    Convenience function to scan folder and run batch test
    
    Args:
        folder_path: Path to folder with images/ and audio/ subdirectories
        language: Language setting (chinese/english)  
        enable_zoom: Enable zoom effects
        config_priority: Instance configuration priority (1-3)
        
    Returns:
        Batch test results dictionary
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
    
    # Execute batch test
    result = operation.execute_batch_test(scenes, language, enable_zoom)
    result["config_used"] = operation.current_config
    return result

def instant_batch_test(scenes: List[Dict], language: str = "chinese", 
                      enable_zoom: bool = True, config_priority: int = 1) -> Dict:
    """
    Convenience function for instant batch video testing
    
    Args:
        scenes: List of scene dictionaries
        language: Language setting
        enable_zoom: Enable zoom effects
        config_priority: Instance configuration priority (1-3)
        
    Returns:
        Batch test results
    """
    operation = InstantInstanceOperationV2(config_priority=config_priority)
    result = operation.execute_batch_test(scenes, language, enable_zoom)
    result["config_used"] = operation.current_config
    return result