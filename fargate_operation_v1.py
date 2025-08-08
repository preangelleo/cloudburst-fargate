#!/usr/bin/env python3
"""
Fargate Operation v1.0 - AWS ECS Fargate Video Processing
Serverless video processing using AWS ECS Fargate for on-demand container execution

Core Features:
- ECS Fargate task management with IAM role support
- Automatic container scaling and cleanup
- Pay-per-second billing with cost tracking
- Zero infrastructure management
- Batch scene processing with parallel execution
- Secure IAM role-based authentication
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

class FargateOperationV1:
    def __init__(self, config_priority=1):
        # Load configuration from environment variables
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize AWS session with IAM role support
        self.session = self._create_aws_session(aws_region)
        self.ecs_client = self.session.client('ecs')
        self.logs_client = self.session.client('logs')
        self.s3_client = self.session.client('s3')
        
        # Fargate Task Configuration Priority List
        self.task_configs = [
            {
                "priority": 1,
                "cpu": "2048",  # 2 vCPU
                "memory": "4096",  # 4GB
                "name": "STANDARD_PROCESSING",
                "description": "Standard video processing - 2 vCPU, 4GB RAM",
                "category": "Balanced",
                "expected_performance": "Good for most video tasks",
                "cost_efficiency": "Best",
                "cost_per_hour": 0.08772  # Approximate Fargate cost
            },
            {
                "priority": 2,
                "cpu": "4096",  # 4 vCPU
                "memory": "8192",  # 8GB
                "name": "HIGH_PERFORMANCE",
                "description": "High performance processing - 4 vCPU, 8GB RAM",
                "category": "Performance",
                "expected_performance": "Faster processing for complex tasks",
                "cost_efficiency": "Medium",
                "cost_per_hour": 0.17544
            },
            {
                "priority": 3,
                "cpu": "8192",  # 8 vCPU
                "memory": "16384",  # 16GB
                "name": "ULTRA_PERFORMANCE",
                "description": "Ultra performance processing - 8 vCPU, 16GB RAM",
                "category": "High Performance",
                "expected_performance": "Very fast processing for complex video tasks",
                "cost_efficiency": "Medium-Low",
                "cost_per_hour": 0.35088
            },
            {
                "priority": 4,
                "cpu": "16384",  # 16 vCPU
                "memory": "32768",  # 32GB
                "name": "MAXIMUM_PERFORMANCE",
                "description": "Maximum performance processing - 16 vCPU, 32GB RAM",
                "category": "Maximum Performance",
                "expected_performance": "Fastest processing for the most demanding tasks",
                "cost_efficiency": "Low",
                "cost_per_hour": 0.70176
            },
            {
                "priority": 5,
                "cpu": "1024",  # 1 vCPU
                "memory": "2048",  # 2GB
                "name": "ECONOMY",
                "description": "Economy processing - 1 vCPU, 2GB RAM",
                "category": "Cost-Optimized",
                "expected_performance": "Slower but most cost-effective",
                "cost_efficiency": "Highest",
                "cost_per_hour": 0.04386
            }
        ]
        
        # Select configuration based on priority
        if 1 <= config_priority <= 5:
            self.current_config = self.task_configs[config_priority - 1]
        else:
            # Fallback order: CPU high to low (16→8→4→2→1 vCPU)
            fallback_order = [3, 2, 1, 0, 4]  # priority 4,3,2,1,5 (16,8,4,2,1 vCPU)
            self.current_config = self.task_configs[fallback_order[0]]  # Default to 16 vCPU (priority 4)
            
        # ECS Configuration (Fixed values - not sensitive)
        self.cluster_name = 'cloudburst-cluster'  # Fixed cluster name
        self.task_definition = 'cloudburst-task:1'  # Fixed task definition
        self.docker_image = 'betashow/video-generation-api:latest'  # Fixed docker image
        
        # Allow override via environment variables if needed
        self.cluster_name = os.getenv('ECS_CLUSTER_NAME', self.cluster_name)
        self.task_definition = os.getenv('ECS_TASK_DEFINITION', self.task_definition)
        self.docker_image = os.getenv('DOCKER_IMAGE', self.docker_image)
        
        # Network Configuration
        subnet_ids_str = os.getenv('AWS_SUBNET_ID', '')
        self.subnet_ids = [subnet.strip() for subnet in subnet_ids_str.split(',') if subnet.strip()]
        
        security_groups_str = os.getenv('AWS_SECURITY_GROUP_ID', '')
        self.security_group_ids = [sg.strip() for sg in security_groups_str.split(',') if sg.strip()]
        
        # API Configuration
        self.api_timeout_minutes = int(os.getenv('API_TIMEOUT_MINUTES', '15'))
        self.api_request_timeout = int(os.getenv('API_REQUEST_TIMEOUT_SECONDS', '300'))
        self.auth_key = os.getenv('VIDEO_API_AUTH_KEY')
        
        # Results directory
        self.results_dir = os.getenv('RESULTS_DIR', '/tmp/cloudburst_fargate_results')
        os.makedirs(self.results_dir, exist_ok=True)
        print(f"📁 Using results directory: {self.results_dir}")
        
        # Validate required configuration
        self._validate_configuration()
        
        # Performance tracking
        self.start_time = None
        self.timing_log = []
        self.batch_results = []
    
    def _create_aws_session(self, aws_region):
        """Create AWS session with IAM role support"""
        import boto3
        
        # Check if IAM role is specified
        role_arn = os.getenv('AWS_ROLE_ARN')
        role_session_name = os.getenv('AWS_ROLE_SESSION_NAME', 'cloudburst-fargate-session')
        external_id = os.getenv('AWS_EXTERNAL_ID')
        
        if role_arn:
            print(f"🔐 Using IAM Role: {role_arn}")
            
            # Create STS client to assume role
            sts_client = boto3.client('sts', region_name=aws_region)
            
            # Prepare assume role parameters
            assume_role_params = {
                'RoleArn': role_arn,
                'RoleSessionName': role_session_name
            }
            
            # Add external ID if provided (for additional security)
            if external_id:
                assume_role_params['ExternalId'] = external_id
                print(f"🔑 Using External ID for additional security")
            
            try:
                # Assume the role
                response = sts_client.assume_role(**assume_role_params)
                credentials = response['Credentials']
                
                print(f"✅ Successfully assumed role")
                print(f"   Session expires: {credentials['Expiration']}")
                
                # Create session with temporary credentials
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=aws_region
                )
                
                return session
                
            except Exception as e:
                print(f"❌ Failed to assume IAM role: {e}")
                print(f"💡 Falling back to default credential chain")
                
        else:
            print(f"🔑 Using default AWS credential chain (Access Keys, Instance Profile, etc.)")
        
        # Fallback to default credential chain
        return boto3.Session(region_name=aws_region)
        
    def _validate_configuration(self):
        """Validate that required ECS configuration is present"""
        # Only validate network configuration (the sensitive/required parts)
        required_configs = {
            'AWS_SUBNET_ID': self.subnet_ids,
            'AWS_SECURITY_GROUP_ID': self.security_group_ids
        }
        
        missing_configs = []
        for config_name, config_value in required_configs.items():
            # Check for empty, None, or insufficient values
            if not config_value or \
               (isinstance(config_value, list) and (len(config_value) == 0 or not any(config_value))):
                missing_configs.append(config_name)
        
        # ECS configuration is now hardcoded, just validate it's not empty
        if not self.cluster_name or not self.task_definition:
            print("⚠️  Warning: ECS cluster or task definition is empty")
            print(f"   Cluster: {self.cluster_name}")
            print(f"   Task Definition: {self.task_definition}")
        
        if missing_configs:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_configs)}\n"
                f"Please check your .env file or set these environment variables.\n"
                f"For ECS Fargate, you need cluster name, task definition, subnet, and security group."
            )
    
    def check_aws_account_validity(self) -> Dict:
        """Check if AWS account and credentials are valid"""
        try:
            # Use STS to get caller identity
            sts_client = self.session.client('sts')
            identity = sts_client.get_caller_identity()
            
            return {
                'valid': True,
                'account_id': identity.get('Account'),
                'user_arn': identity.get('Arn'),
                'message': 'AWS credentials are valid'
            }
        except Exception as e:
            return {
                'valid': False,
                'message': f'AWS credentials invalid: {str(e)}'
            }
    
    def log_timing(self, event: str):
        """Log timing for performance analysis"""
        if self.start_time is None:
            self.start_time = time.time()
            
        elapsed = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.timing_log.append(f"[{timestamp}] +{elapsed:6.2f}s - {event}")
        print(f"⏱️  [{timestamp}] +{elapsed:6.2f}s - {event}")
    
    def calculate_fargate_cost(self, runtime_seconds: float, task_count: int = 1) -> Dict:
        """Calculate Fargate cost based on runtime and resource configuration"""
        # Fargate pricing (US East 1, Linux/x86)
        vcpu_per_second = 0.000011244
        memory_per_gb_per_second = 0.000001235
        
        # Current config resources
        vcpu_count = int(self.current_config["cpu"]) / 1024  # Convert from CPU units
        memory_gb = int(self.current_config["memory"]) / 1024  # Convert from MB
        
        # Calculate costs
        vcpu_cost = vcpu_count * vcpu_per_second * runtime_seconds
        memory_cost = memory_gb * memory_per_gb_per_second * runtime_seconds
        task_cost = vcpu_cost + memory_cost
        total_cost = task_cost * task_count
        
        runtime_minutes = runtime_seconds / 60
        runtime_hours = runtime_seconds / 3600
        
        # Calculate cost per hour
        cost_per_hour = task_cost * 3600  # Cost for 1 hour
        
        return {
            "fargate_config": f"{vcpu_count}vCPU/{memory_gb}GB",
            "runtime_seconds": runtime_seconds,
            "runtime_minutes": runtime_minutes,
            "runtime_hours": runtime_hours,
            "cost_per_task_usd": round(task_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "task_count": task_count,
            "cost_per_hour": round(cost_per_hour, 6),  # Add missing cost_per_hour
            "cost_breakdown": {
                "vcpu_cost": round(vcpu_cost, 6),
                "memory_cost": round(memory_cost, 6),
                "calculation": f"{vcpu_count}vCPU × ${vcpu_per_second}/sec × {runtime_seconds}s + {memory_gb}GB × ${memory_per_gb_per_second}/sec × {runtime_seconds}s"
            }
        }
    
    def scan_scenes_from_folder(self, folder_path: str) -> List[Dict]:
        """Scan a folder and automatically generate scene list"""
        scenes = []
        
        images_dir = os.path.join(folder_path, "images")
        audio_dir = os.path.join(folder_path, "audio")
        
        if not os.path.exists(images_dir) or not os.path.exists(audio_dir):
            raise ValueError(f"Missing images/ or audio/ directories in {folder_path}")
        
        # Find image files and match with audio/subtitle
        image_pattern = os.path.join(images_dir, "scene_*.png")
        image_files = sorted(glob.glob(image_pattern))
        
        for image_file in image_files:
            filename = os.path.basename(image_file)
            scene_name = filename.replace('.png', '')
            
            audio_file = os.path.join(audio_dir, f"{scene_name}.mp3")
            subtitle_file = os.path.join(audio_dir, f"{scene_name}.srt")
            
            if os.path.exists(audio_file):
                scene = {
                    "scene_name": scene_name,
                    "image_path": image_file,  # Fixed field name to match _prepare_scene_payload
                    "audio_path": audio_file,  # Fixed field name to match _prepare_scene_payload
                    "subtitle_path": subtitle_file if os.path.exists(subtitle_file) else None  # Fixed field name
                }
                scenes.append(scene)
                print(f"📽️ Found scene: {scene_name} (subtitle: {'✅' if scene['subtitle_path'] else '❌'})")
        
        print(f"🎬 Total scenes found: {len(scenes)}")
        return scenes
    
    def start_fargate_task(self, scene: Dict, **kwargs) -> Optional[str]:
        """Start a single Fargate task for video processing"""
        try:
            # Prepare environment variables for the container
            environment = [
                {'name': 'SCENE_NAME', 'value': scene['scene_name']},
                {'name': 'ENABLE_ZOOM', 'value': str(kwargs.get('enable_zoom', True))},
                {'name': 'LANGUAGE', 'value': kwargs.get('language', 'english')},
                {'name': 'AWS_DEFAULT_REGION', 'value': os.getenv('AWS_REGION', 'us-east-1')}
            ]
            
            # Add subtitle if present
            if scene.get('subtitle_path'):
                environment.append({'name': 'HAS_SUBTITLE', 'value': 'true'})
            
            # Start the task
            self.log_timing(f"🚀 Starting Fargate task for {scene['scene_name']}")
            
            response = self.ecs_client.run_task(
                cluster=self.cluster_name,
                taskDefinition=self.task_definition,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': self.subnet_ids,
                        'securityGroups': self.security_group_ids,
                        'assignPublicIp': 'ENABLED'
                    }
                },
                overrides={
                    'cpu': self.current_config['cpu'],
                    'memory': self.current_config['memory'],
                    'containerOverrides': [{
                        'name': 'cloudburst-processor',
                        'environment': environment,
                        'cpu': int(self.current_config['cpu']),
                        'memory': int(self.current_config['memory'])
                    }]
                },
                tags=[
                    {'key': 'Project', 'value': 'CloudBurst'},
                    {'key': 'Scene', 'value': scene['scene_name']},
                    {'key': 'Language', 'value': kwargs.get('language', 'english')},
                    {'key': 'CreatedBy', 'value': 'animagent'},
                    {'key': 'Purpose', 'value': 'video-generation'}
                ]
            )
            
            if response['tasks']:
                task_arn = response['tasks'][0]['taskArn']
                self.log_timing(f"✅ Task started: {task_arn.split('/')[-1]}")
                return task_arn
            else:
                self.log_timing(f"❌ Failed to start task: No task in response")
                return None
                
        except Exception as e:
            self.log_timing(f"❌ Failed to start task: {str(e)}")
            return None
    
    def wait_for_task_completion(self, task_arn: str, scene_name: str) -> Dict:
        """Wait for a single task to complete and return results"""
        self.log_timing(f"⏳ Waiting for task completion: {scene_name}")
        
        start_time = time.time()
        max_wait_time = self.api_timeout_minutes * 60  # Convert to seconds
        
        while True:
            try:
                response = self.ecs_client.describe_tasks(
                    cluster=self.cluster_name,
                    tasks=[task_arn]
                )
                
                if not response['tasks']:
                    return {
                        'success': False,
                        'scene_name': scene_name,
                        'error': 'Task not found'
                    }
                
                task = response['tasks'][0]
                status = task['lastStatus']
                
                # Check if task completed
                if status == 'STOPPED':
                    # Check exit code
                    containers = task.get('containers', [])
                    if containers:
                        exit_code = containers[0].get('exitCode', 1)
                        if exit_code == 0:
                            runtime = time.time() - start_time
                            self.log_timing(f"✅ Task completed successfully: {scene_name} ({runtime:.1f}s)")
                            return {
                                'success': True,
                                'scene_name': scene_name,
                                'runtime_seconds': runtime,
                                'task_arn': task_arn
                            }
                        else:
                            # Get failure reason
                            failure_reason = containers[0].get('reason', 'Unknown error')
                            self.log_timing(f"❌ Task failed: {scene_name} - {failure_reason}")
                            return {
                                'success': False,
                                'scene_name': scene_name,
                                'error': f'Task failed with exit code {exit_code}: {failure_reason}'
                            }
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > max_wait_time:
                    self.log_timing(f"⏰ Task timeout: {scene_name}")
                    return {
                        'success': False,
                        'scene_name': scene_name,
                        'error': f'Task timeout after {max_wait_time/60:.1f} minutes'
                    }
                
                # Update status
                if elapsed % 30 == 0:  # Log every 30 seconds
                    self.log_timing(f"📊 Task status: {scene_name} - {status}")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                return {
                    'success': False,
                    'scene_name': scene_name,
                    'error': f'Error monitoring task: {str(e)}'
                }
    
    def _wait_for_public_ip(self, task_arn: str, max_wait: int = 180) -> str:
        """Wait for Fargate task to get public IP"""
        import time
        
        ec2 = self.session.client('ec2')
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            try:
                response = self.ecs_client.describe_tasks(
                    cluster=self.cluster_name,
                    tasks=[task_arn]
                )
                
                if response['tasks']:
                    task = response['tasks'][0]
                    status = task['lastStatus']
                    
                    if status == 'RUNNING':
                        # Get public IP
                        attachments = task.get('attachments', [])
                        for attachment in attachments:
                            if attachment['type'] == 'ElasticNetworkInterface':
                                for detail in attachment['details']:
                                    if detail['name'] == 'networkInterfaceId':
                                        eni_id = detail['value']
                                        
                                        eni_response = ec2.describe_network_interfaces(
                                            NetworkInterfaceIds=[eni_id]
                                        )
                                        
                                        if eni_response['NetworkInterfaces']:
                                            association = eni_response['NetworkInterfaces'][0].get('Association', {})
                                            public_ip = association.get('PublicIp')
                                            if public_ip:
                                                return public_ip
                
                time.sleep(10)
                
            except Exception as e:
                self.log_timing(f"⚠️  Error checking IP: {e}")
                time.sleep(10)
        
        return None
    
    def _wait_for_api_ready(self, api_url: str, max_attempts: int = 20) -> bool:
        """Wait for Flask API to become ready"""
        import requests
        import time
        
        for attempt in range(max_attempts):
            try:
                health_url = f"{api_url}/health"
                response = requests.get(health_url, timeout=10)
                
                if response.status_code == 200:
                    self.log_timing(f"✅ API server is ready (attempt {attempt + 1})")
                    return True
                    
            except requests.exceptions.ConnectionError:
                self.log_timing(f"🔄 Flask server starting... (attempt {attempt + 1}/{max_attempts})")
            except Exception as e:
                self.log_timing(f"⚠️  Connection error: {e}")
            
            time.sleep(30)
        
        return False
    
    def _prepare_scene_payload(self, scene: Dict, language: str, enable_zoom: bool, 
                              watermark_path: str, is_portrait: bool, 
                              background_box: bool, background_opacity: float) -> Dict:
        """Prepare API payload for scene processing (like batch_fargate_test.py)"""
        import base64
        import os
        
        # Read and encode files
        image_path = scene['image_path']
        audio_path = scene['audio_path'] 
        subtitle_path = scene['subtitle_path']
        
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(audio_path, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            subtitle_content = f.read()
            subtitle_b64 = base64.b64encode(subtitle_content.encode('utf-8')).decode('utf-8')
        
        # Prepare watermark if provided
        watermark_b64 = None
        if watermark_path and os.path.exists(watermark_path):
            with open(watermark_path, 'rb') as f:
                watermark_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Create API payload
        payload = {
            # Required parameters
            "input_image": image_b64,
            "input_audio": audio_b64,
            
            # Optional file parameters  
            "subtitle": subtitle_b64,
            
            # Video settings
            "is_portrait": is_portrait,
            "language": language,
            "output_filename": f"{scene['scene_name']}.mp4",
            
            # Effects
            "effects": ["zoom_in", "zoom_out"] if enable_zoom else [],
            
            # Subtitle styling
            "font_size": None,  # Auto-calculate
            "outline_color": "&H00000000",  # Black outline
            "background_box": background_box,
            "background_opacity": background_opacity
        }
        
        # Add watermark if available
        if watermark_b64:
            payload["watermark"] = watermark_b64
        
        return payload
    
    def execute_batch(self, scenes: List[Dict], language: str = 'english', 
                     enable_zoom: bool = True, auto_terminate: bool = True,
                     saving_dir: str = None, **kwargs) -> Dict:
        """Execute batch processing using a single Fargate task with real API processing"""
        import requests
        import base64
        
        self.log_timing(f"=== CLOUDBURST FARGATE BATCH START ({len(scenes)} scenes) ===")
        
        batch_start_time = time.time()
        results = []
        successful_scenes = 0
        task_arn = None
        public_ip = None
        downloaded_files = []
        
        # Get additional parameters from kwargs
        watermark_path = kwargs.get('watermark_path')
        is_portrait = kwargs.get('is_portrait', False) 
        background_box = kwargs.get('background_box', True)
        background_opacity = kwargs.get('background_opacity', 0.2)
        
        # Create output directory
        if saving_dir is None:
            saving_dir = self.results_dir
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(saving_dir, f"batch_{timestamp}")
        os.makedirs(batch_dir, exist_ok=True)
        
        try:
            if not scenes:
                raise ValueError("No scenes provided for batch processing")
            
            self.log_timing(f"=== Starting Fargate task with Flask API service ===")
            
            # Start Fargate task (this will run the Docker container with Flask API)
            first_scene = scenes[0]  # Use first scene for task startup
            task_arn = self.start_fargate_task(first_scene, language=language, enable_zoom=enable_zoom)
            
            if not task_arn:
                raise Exception("Failed to start Fargate task")
            
            self.log_timing(f"✅ Fargate task started: {task_arn}")
            
            # Wait for task to get public IP and start Flask API
            self.log_timing("⏳ Waiting for Flask API to become ready...")
            
            # Get public IP (simplified version of batch_fargate_test.py logic)
            public_ip = self._wait_for_public_ip(task_arn)
            if not public_ip:
                raise Exception("Failed to get public IP for Fargate task")
            
            self.log_timing(f"✅ Public IP obtained: {public_ip}")
            
            # Wait for Flask API to be ready
            api_url = f"http://{public_ip}:5000"
            if not self._wait_for_api_ready(api_url):
                raise Exception("Flask API did not become ready")
            
            self.log_timing("✅ Flask API is ready - starting scene processing")
            
            # Process each scene individually with real API calls
            for i, scene in enumerate(scenes, 1):
                scene_name = scene['scene_name']
                self.log_timing(f"🎬 Processing Scene {i}/{len(scenes)}: {scene_name}")
                
                scene_start_time = time.time()
                
                try:
                    # Prepare API payload (like batch_fargate_test.py)
                    api_payload = self._prepare_scene_payload(
                        scene, language, enable_zoom, watermark_path, 
                        is_portrait, background_box, background_opacity
                    )
                    
                    # Send API request
                    self.log_timing(f"📡 Sending API request for {scene_name}")
                    response = requests.post(
                        f"{api_url}/create_video_onestep",
                        json=api_payload,
                        timeout=600  # 10 minutes timeout
                    )
                    
                    scene_end_time = time.time()
                    scene_duration = scene_end_time - scene_start_time
                    
                    if response.status_code == 200:
                        result_data = response.json()
                        
                        # Immediately download the file (efficient approach!)
                        download_success = False
                        local_file_path = None
                        file_size = 0
                        
                        if result_data.get('file_id'):
                            download_url = f"{api_url}/download/{result_data['file_id']}"
                            output_file = os.path.join(batch_dir, f"{scene_name}.mp4")
                            
                            self.log_timing(f"📥 Downloading {scene_name} immediately...")
                            
                            try:
                                dl_response = requests.get(download_url, timeout=120)
                                if dl_response.status_code == 200:
                                    with open(output_file, 'wb') as f:
                                        f.write(dl_response.content)
                                    
                                    file_size = len(dl_response.content)
                                    local_file_path = output_file
                                    downloaded_files.append(output_file)
                                    download_success = True
                                    
                                    self.log_timing(f"✅ {scene_name} downloaded ({file_size/1024/1024:.2f}MB)")
                                else:
                                    self.log_timing(f"❌ Download failed for {scene_name}: HTTP {dl_response.status_code}")
                            except Exception as dl_e:
                                self.log_timing(f"❌ Download error for {scene_name}: {dl_e}")
                        
                        # Record scene result
                        scene_result = {
                            'success': True,
                            'scene_name': scene_name,
                            'processing_time': scene_duration,
                            'file_id': result_data.get('file_id'),
                            'download_endpoint': result_data.get('download_endpoint'),
                            'filename': result_data.get('filename'),
                            'size': file_size,
                            'scenario': result_data.get('scenario', 'unknown'),
                            'local_file': local_file_path,
                            'download_success': download_success
                        }
                        
                        results.append(scene_result)
                        successful_scenes += 1
                        
                        self.log_timing(f"✅ Scene {scene_name} completed successfully!")
                        
                    else:
                        # API request failed
                        scene_result = {
                            'success': False,
                            'scene_name': scene_name,
                            'processing_time': scene_duration,
                            'error': f"API request failed: HTTP {response.status_code}"
                        }
                        results.append(scene_result)
                        self.log_timing(f"❌ Scene {scene_name} failed: HTTP {response.status_code}")
                        
                except Exception as scene_e:
                    scene_result = {
                        'success': False,
                        'scene_name': scene_name,
                        'processing_time': time.time() - scene_start_time,
                        'error': str(scene_e)
                    }
                    results.append(scene_result)
                    self.log_timing(f"❌ Scene {scene_name} error: {scene_e}")
            
            self.log_timing(f"🎬 Batch processing completed: {successful_scenes}/{len(scenes)} successful")
            
        except Exception as e:
            self.log_timing(f"❌ Batch processing error: {e}")
            # Mark all scenes as failed if batch setup failed
            if not results:  # Only if no scenes were processed yet
                for scene in scenes:
                    results.append({
                        'success': False,
                        'scene_name': scene['scene_name'],
                        'error': str(e)
                    })
        
        # Calculate final costs and timing
        total_runtime = time.time() - batch_start_time
        cost_info = self.calculate_fargate_cost(total_runtime, 1)  # Single task for batch
        
        self.log_timing(f"=== BATCH PROCESSING COMPLETED: {successful_scenes}/{len(scenes)} scenes successful ===")
        
        return {
            'success': successful_scenes > 0,
            'successful_scenes': successful_scenes,
            'failed_scenes': len(scenes) - successful_scenes,
            'total_scenes': len(scenes),
            'cost_usd': cost_info['total_cost_usd'],
            'total_time': total_runtime,
            'batch_results': results,
            'fargate_config': cost_info['fargate_config'],
            'output_directory': batch_dir,
            'download_dir': batch_dir,
            'downloaded_files': downloaded_files,  # Real downloaded files list
            'download_count': len(downloaded_files),
            'cost_breakdown': cost_info,
            'task_arn': task_arn,  # Add task_arn for cleanup
            'public_ip': public_ip  # For debugging
        }
    
    def list_running_tasks(self, filter_animagent_only: bool = True) -> List[Dict]:
        """List running Fargate tasks in the cluster
        
        Args:
            filter_animagent_only: If True, only return tasks created by animagent
        """
        try:
            # List all running tasks
            response = self.ecs_client.list_tasks(
                cluster=self.cluster_name,
                desiredStatus='RUNNING'
            )
            
            running_task_arns = response.get('taskArns', [])
            
            if not running_task_arns:
                return []
            
            # Get detailed information about each task
            tasks_response = self.ecs_client.describe_tasks(
                cluster=self.cluster_name,
                tasks=running_task_arns
            )
            
            running_tasks = []
            for task in tasks_response.get('tasks', []):
                task_arn = task['taskArn']
                
                # If filtering is enabled, check task tags
                if filter_animagent_only:
                    try:
                        # Get task tags
                        tags_response = self.ecs_client.list_tags_for_resource(
                            resourceArn=task_arn
                        )
                        tags = tags_response.get('tags', [])
                        
                        # Check if this task was created by animagent
                        is_animagent_task = False
                        for tag in tags:
                            if tag.get('key') == 'CreatedBy' and tag.get('value') == 'animagent':
                                is_animagent_task = True
                                break
                        
                        # Skip non-animagent tasks
                        if not is_animagent_task:
                            continue
                    except Exception as e:
                        # If we can't get tags, skip this task when filtering
                        print(f"⚠️ Could not get tags for task {task_arn}: {str(e)}")
                        continue
                
                # Extract relevant information
                task_info = {
                    'task_arn': task_arn,
                    'task_definition': task.get('taskDefinitionArn', '').split('/')[-1],
                    'status': task['lastStatus'],
                    'started_at': task.get('startedAt', ''),
                    'cpu': task.get('cpu', ''),
                    'memory': task.get('memory', ''),
                    'public_ip': None,
                    'tags': tags if filter_animagent_only else []
                }
                
                # Try to get public IP
                attachments = task.get('attachments', [])
                for attachment in attachments:
                    if attachment.get('type') == 'ElasticNetworkInterface':
                        for detail in attachment.get('details', []):
                            if detail.get('name') == 'networkInterfaceId':
                                try:
                                    # Get ENI details
                                    eni_id = detail['value']
                                    ec2 = self.session.client('ec2')
                                    eni_response = ec2.describe_network_interfaces(
                                        NetworkInterfaceIds=[eni_id]
                                    )
                                    if eni_response['NetworkInterfaces']:
                                        public_ip = eni_response['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
                                        if public_ip:
                                            task_info['public_ip'] = public_ip
                                except:
                                    pass
                
                running_tasks.append(task_info)
            
            return running_tasks
            
        except Exception as e:
            print(f"❌ Error listing running tasks: {str(e)}")
            return []
    
    def cleanup_all_tasks(self, reason: str = "Cleanup requested", filter_animagent_only: bool = True) -> Dict:
        """Terminate running Fargate tasks in the cluster
        
        Args:
            reason: Reason for termination
            filter_animagent_only: If True, only terminate tasks created by animagent
        """
        try:
            # Get running tasks (filtered by default)
            running_tasks = self.list_running_tasks(filter_animagent_only=filter_animagent_only)
            
            if not running_tasks:
                return {
                    'success': True,
                    'message': 'No running tasks found',
                    'terminated_count': 0
                }
            
            terminated = []
            failed = []
            
            # Terminate each task
            for task in running_tasks:
                task_arn = task['task_arn']
                try:
                    self.ecs_client.stop_task(
                        cluster=self.cluster_name,
                        task=task_arn,
                        reason=reason
                    )
                    terminated.append(task_arn)
                    print(f"✅ Terminated task: {task_arn}")
                except Exception as e:
                    failed.append({'task_arn': task_arn, 'error': str(e)})
                    print(f"❌ Failed to terminate task {task_arn}: {str(e)}")
            
            return {
                'success': len(failed) == 0,
                'terminated_count': len(terminated),
                'failed_count': len(failed),
                'terminated_tasks': terminated,
                'failed_tasks': failed,
                'message': f'Terminated {len(terminated)} tasks, {len(failed)} failed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error during cleanup: {str(e)}',
                'terminated_count': 0
            }

# Convenience functions for backward compatibility
def scan_and_test_folder(folder_path: str, language: str = 'english', 
                        enable_zoom: bool = True, saving_dir: str = None) -> Dict:
    """Scan folder and process with Fargate"""
    processor = FargateOperationV1()
    scenes = processor.scan_scenes_from_folder(folder_path)
    return processor.execute_batch(scenes, language=language, enable_zoom=enable_zoom, 
                                  auto_terminate=True, saving_dir=saving_dir)



def calculate_optimal_batch_distribution(total_scenes: int, 
                                       scenes_per_batch: int = 10,
                                       max_parallel_tasks: int = 10,
                                       min_scenes_per_batch: int = 5) -> Dict:
    """
    Calculate optimal distribution of scenes across Fargate tasks
    
    Args:
        total_scenes: Total number of scenes to process
        scenes_per_batch: User's preferred scenes per batch
        max_parallel_tasks: Maximum Fargate tasks to run in parallel
        min_scenes_per_batch: Minimum scenes to justify task startup cost
        
    Returns:
        Dict with distribution plan:
        {
            "num_tasks": int,  # Actual Fargate tasks to use
            "batch_distribution": List[int],  # Number of scenes per batch
            "total_batches": int,  # Same as num_tasks
            "strategy": str,  # Description of strategy used
            "warnings": List[str],  # Any warnings about parameter adjustments
        }
    """
    warnings = []
    
    # Case 1: Total scenes exceeds or equals what we can handle with preferred batch size
    if total_scenes >= scenes_per_batch * max_parallel_tasks:
        # Use all available tasks and distribute evenly
        num_tasks = max_parallel_tasks
        base_scenes = total_scenes // num_tasks
        remainder = total_scenes % num_tasks
        
        # Create distribution: first 'remainder' tasks get +1 scene
        batch_distribution = []
        for i in range(num_tasks):
            batch_distribution.append(base_scenes + (1 if i < remainder else 0))
        
        strategy = f"Large batch: Using all {num_tasks} Fargate tasks with ~{base_scenes} scenes each"
        warnings.append(f"Overriding scenes_per_batch ({scenes_per_batch}) to handle {total_scenes} scenes")
        
        return {
            "num_tasks": num_tasks,
            "batch_distribution": batch_distribution,
            "total_batches": num_tasks,
            "strategy": strategy,
            "warnings": warnings
        }
    
    # Case 2: Total scenes can be handled with preferred batch size
    # Start with even distribution across max tasks
    num_tasks = max_parallel_tasks
    
    # Keep reducing tasks until each has >= min_scenes_per_batch
    while num_tasks > 1:
        base_scenes = total_scenes // num_tasks
        remainder = total_scenes % num_tasks
        
        min_batch_size = base_scenes
        
        if min_batch_size >= min_scenes_per_batch:
            # This distribution works!
            batch_distribution = []
            for i in range(num_tasks):
                batch_distribution.append(base_scenes + (1 if i < remainder else 0))
            
            # Check if we're close to user's preferred scenes_per_batch
            avg_scenes = total_scenes / num_tasks
            if abs(avg_scenes - scenes_per_batch) <= 2:
                strategy = f"Optimal: {num_tasks} Fargate tasks with ~{int(avg_scenes)} scenes each"
            else:
                strategy = f"Adjusted: {num_tasks} Fargate tasks to maintain minimum {min_scenes_per_batch} scenes per batch"
                if avg_scenes > scenes_per_batch:
                    warnings.append(f"Using fewer tasks to ensure each has >= {min_scenes_per_batch} scenes")
            
            return {
                "num_tasks": num_tasks,
                "batch_distribution": batch_distribution,
                "total_batches": num_tasks,
                "strategy": strategy,
                "warnings": warnings
            }
        
        # Reduce tasks and try again
        num_tasks -= 1
    
    # If we get here, use single task
    return {
        "num_tasks": 1,
        "batch_distribution": [total_scenes],
        "total_batches": 1,
        "strategy": f"Single Fargate task: {total_scenes} scenes too small to parallelize efficiently",
        "warnings": [f"Using single task as {total_scenes} scenes < {min_scenes_per_batch * 2}"]
    }


def execute_parallel_batches(scenes: List[Dict], 
                           scenes_per_batch: int = 10,
                           language: str = "chinese",
                           enable_zoom: bool = True,
                           config_priority: int = 4,
                           max_parallel_tasks: int = 10,  # Changed from max_parallel_instances
                           min_scenes_per_batch: int = 5,
                           watermark_path: str = None,
                           is_portrait: bool = False,
                           saving_dir: str = None,
                           background_box: bool = True,
                           background_opacity: float = 0.2) -> Dict:
    """
    Execute large scene lists in parallel across multiple Fargate tasks
    
    This function splits a large list of scenes into smaller batches and processes
    them simultaneously on separate AWS Fargate containers for maximum speed.
    
    Smart Distribution Logic:
    - If total scenes <= scenes_per_batch * max_parallel_tasks:
      Uses requested scenes_per_batch (may use fewer tasks)
    - If total scenes > scenes_per_batch * max_parallel_tasks:
      Redistributes evenly across exactly max_parallel_tasks
      
    Examples:
    - 50 scenes, scenes_per_batch=10, max_tasks=10 → 5 tasks × 10 scenes
    - 120 scenes, scenes_per_batch=10, max_tasks=10 → 10 tasks × 12 scenes
    - 101 scenes, scenes_per_batch=10, max_tasks=10 → 10 tasks (9×10 + 1×11)
    
    Args:
        scenes: List of all scene dictionaries to process
        scenes_per_batch: Preferred number of scenes per task (default: 10)
        language: Language setting (chinese/english)
        enable_zoom: Enable zoom effects for all scenes
        config_priority: Fargate configuration priority (1-5)
        max_parallel_tasks: Maximum number of Fargate tasks to run in parallel
        min_scenes_per_batch: Minimum scenes per task to justify startup cost (default: 5)
        watermark_path: Optional path to watermark image
        is_portrait: Whether video is in portrait mode
        saving_dir: Directory to save downloaded files (default: ./cloudburst_fargate_results/)
        background_box: Whether to show subtitle background (default: True)
        background_opacity: Subtitle background transparency 0-1 (default: 0.2)
        
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
            "tasks_used": int,
            "batch_results": [...],  # All scene results ordered by scene_name
            "task_results": [...]  # Details per Fargate task for debugging
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
        max_parallel_tasks=max_parallel_tasks,
        min_scenes_per_batch=min_scenes_per_batch
    )
    
    # Extract values from distribution plan
    num_tasks = distribution_plan["num_tasks"]
    batch_distribution = distribution_plan["batch_distribution"]
    
    print(f"🚀 Starting parallel Fargate batch processing")
    print(f"📊 Total scenes: {total_scenes}")
    print(f"🎯 Fargate tasks to use: {num_tasks}")
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
    task_results = []
    active_tasks = []  # Track all task ARNs for cleanup
    
    def process_batch(batch_info: Dict) -> Dict:
        """Process a single batch on its own Fargate task"""
        batch_id = batch_info["batch_id"]
        batch_scenes = batch_info["scenes"]
        
        print(f"\n🔄 Batch {batch_id}: Processing {len(batch_scenes)} scenes on Fargate")
        
        try:
            # Create Fargate processor for this batch
            operation = FargateOperationV1(config_priority=config_priority)
            
            # Execute batch (keep task alive for downloads)
            result = operation.execute_batch(
                scenes=batch_scenes,
                language=language,
                enable_zoom=enable_zoom,
                auto_terminate=False,  # Keep alive for downloads
                watermark_path=watermark_path,
                is_portrait=is_portrait,
                saving_dir=saving_dir,  # Pass saving_dir for immediate downloads
                background_box=background_box,
                background_opacity=background_opacity
            )
            
            # Track task ARN for cleanup
            if result.get("task_arn"):
                with results_lock:
                    active_tasks.append({
                        "batch_id": batch_id,
                        "task_arn": result["task_arn"],
                        "operation": operation
                    })
            
            # Add batch metadata
            result["batch_id"] = batch_id
            result["start_index"] = batch_info["start_index"]
            result["end_index"] = batch_info["end_index"]
            result["task_config"] = operation.current_config["name"]
            
            # Download results before terminating task
            if result.get("success") and result.get("batch_results"):
                print(f"📥 Batch {batch_id}: Downloading {len(result['batch_results'])} videos...")
                
                # Create directory for this batch with priority:
                # 1. User-provided saving_dir
                # 2. RESULTS_DIR from environment/.env
                # 3. Default: ./cloudburst_fargate_results/
                if saving_dir:
                    # Priority 1: Use user-provided directory
                    base_dir = saving_dir
                elif os.getenv('RESULTS_DIR'):
                    # Priority 2: Use RESULTS_DIR from environment
                    base_dir = os.getenv('RESULTS_DIR')
                else:
                    # Priority 3: Default fallback
                    base_dir = os.path.join(os.getcwd(), "cloudburst_fargate_results")
                
                batch_dir = os.path.join(base_dir, f"batch_{batch_id}_{int(time.time())}")
                os.makedirs(batch_dir, exist_ok=True)
                
                # Check if files were downloaded by execute_batch (now implements real processing)
                downloaded_count = result.get("download_count", 0)
                downloaded_files = result.get("downloaded_files", [])
                
                if downloaded_count > 0 and downloaded_files:
                    # Files were downloaded during processing - efficient approach!
                    print(f"✅ Batch {batch_id}: {downloaded_count} files downloaded immediately during processing")
                    print(f"📁 Files saved to: {result.get('download_dir', 'unknown')}")
                    
                    # List downloaded files
                    for file_path in downloaded_files:
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path) / 1024 / 1024
                            print(f"   🎬 {os.path.basename(file_path)} ({file_size:.2f}MB)")
                else:
                    # No files downloaded - either failed processing or download issues
                    print(f"⚠️ Batch {batch_id}: No files downloaded (processing may have failed)")
                
                # Always terminate the task after processing
                if result.get('task_arn'):
                    try:
                        # Use ECS client to stop task directly
                        operation.ecs_client.stop_task(
                            cluster=operation.cluster_name,
                            task=result['task_arn'],
                            reason='Batch processing completed'
                        )
                        
                        # Calculate final cost using the task's own timing
                        task_runtime = result.get('total_time', 0)  # Use the task's actual runtime
                        if task_runtime > 0:
                            final_cost_info = operation.calculate_fargate_cost(task_runtime, 1)
                            result["final_cost_usd"] = final_cost_info["total_cost_usd"]
                        else:
                            result["final_cost_usd"] = result.get("cost_usd", 0)
                        
                        print(f"✅ Batch {batch_id}: Fargate task terminated (final cost: ${result['final_cost_usd']:.4f})")
                        
                    except Exception as e:
                        print(f"⚠️ Batch {batch_id}: Failed to terminate task: {str(e)}")
            else:
                # CRITICAL: If batch failed or has no results, we must still terminate the task
                print(f"⚠️ Batch {batch_id}: Failed or no results - terminating task immediately")
                if result.get('task_arn'):
                    try:
                        operation.ecs_client.stop_task(
                            cluster=operation.cluster_name,
                            task=result['task_arn'],
                            reason='Batch processing failed'
                        )
                        print(f"✅ Batch {batch_id}: Fargate task terminated successfully")
                    except Exception as term_error:
                        print(f"❌ Batch {batch_id}: Failed to terminate task: {str(term_error)}")
                        # Task will be caught by the finally block emergency cleanup
            
            with results_lock:
                task_results.append(result)
            
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
                task_results.append(error_result)
                
            return error_result
    
    # Track cleanup status
    cleanup_performed = False
    
    try:
        # Process batches in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_tasks) as executor:
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
    
        # Sort task results by batch_id to maintain order
        task_results.sort(key=lambda x: x.get("batch_id", 0))
    
        for task_result in task_results:
            if task_result.get("success", False):
                # Use final_cost_usd if available (includes download time)
                total_cost += task_result.get("final_cost_usd", task_result.get("cost_usd", 0))
                total_processing_time += task_result.get("total_time", 0)
                successful_scenes += task_result.get("successful_scenes", 0)
                failed_scenes += task_result.get("failed_scenes", 0)
                
                # Collect all scene results
                for scene_result in task_result.get("batch_results", []):
                    all_scene_results.append(scene_result)
                
                # Collect downloaded files
                for file_path in task_result.get("downloaded_files", []):
                    all_downloaded_files.append({
                        "batch_id": task_result.get("batch_id"),
                        "file_path": file_path,
                        "temp_dir": task_result.get("download_dir")
                    })
            else:
                # Even failed batches count their scenes as failed
                failed_scenes += task_result.get("failed_scenes", 0)
    
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
        "time_saved": total_processing_time - parallel_time if num_tasks > 1 else 0,
        "tasks_used": num_tasks,
        "scenes_per_batch": scenes_per_batch,
        "batch_results": all_scene_results,  # All scenes sorted by name
        "downloaded_files": all_downloaded_files,  # All downloaded file paths
        "task_results": task_results,  # Per-task details
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
        # CRITICAL: Emergency cleanup - terminate any Fargate tasks that might still be running
        if not cleanup_performed and active_tasks:
            print(f"\n⚠️  EMERGENCY CLEANUP: Terminating {len(active_tasks)} Fargate tasks...")
            
            for task_info in active_tasks:
                try:
                    task_arn = task_info["task_arn"]
                    batch_id = task_info["batch_id"]
                    operation = task_info["operation"]
                    
                    print(f"🛑 Terminating Fargate task for batch {batch_id} (ARN: {task_arn})")
                    operation.ecs_client.stop_task(
                        cluster=operation.cluster_name,
                        task=task_arn,
                        reason='Emergency cleanup'
                    )
                    
                except Exception as e:
                    print(f"❌ Failed to terminate task {task_arn}: {str(e)}")
                    # Try direct ECS termination as last resort
                    try:
                        import boto3
                        ecs = boto3.client('ecs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
                        cluster_name = operation.cluster_name if hasattr(operation, 'cluster_name') else 'cloudburst-cluster'
                        ecs.stop_task(cluster=cluster_name, task=task_arn, reason='Emergency cleanup')
                        print(f"✅ Terminated via direct ECS API call")
                    except Exception as direct_error:
                        print(f"🚨 CRITICAL: Could not terminate task {task_arn} - manual cleanup required! Error: {direct_error}")
            
            print(f"⚠️  Emergency cleanup completed\n")


