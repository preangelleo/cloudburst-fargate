# CloudBurst Fargate - 无服务器视频处理框架

[![PyPI version](https://badge.fury.io/py/cloudburst-fargate.svg)](https://pypi.org/project/cloudburst-fargate/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS ECS](https://img.shields.io/badge/AWS-ECS%20Fargate-orange.svg)](https://aws.amazon.com/fargate/)

我的第二个开源项目，现已升级到 **AWS ECS Fargate** 架构！🚀

**作者**: Leo Wang ([leowang.net](https://leowang.net))  
**邮箱**: me@leowang.net  
**许可证**: MIT

> **📚 相关项目**: 
> - **原版 CloudBurst (EC2)**: https://github.com/preangelleo/cloudburst
> - **视频生成 API**: https://github.com/preangelleo/video-generation-docker
> - **English Version**: [README.md](./README.md)

## 这是什么？

一个生产就绪的 Python 框架，使用 **AWS ECS Fargate** 提供无服务器、按需视频生成服务，支持 **并行处理能力**。

**核心价值**：当你的应用需要生成视频时（使用我们的 [视频生成 API](https://github.com/preangelleo/video-generation-docker)），这个框架会：
- 🚀 **30秒内**启动 Fargate 容器（相比 EC2 的 2+ 分钟）
- ⚡ **并行处理**：跨多个并发容器处理多个场景
- 🎬 零基础设施管理地处理你的视频生成请求
- 📥 自动下载完成的视频，采用"处理一个→下载一个"的高效模式
- 🛑 处理完成后容器自动终止
- 💰 按秒计费，**无闲置成本**

**完美适用于**：需要可扩展的无服务器视频处理，但不想管理 EC2 实例复杂性的生产应用。

## 📦 安装

### 从 PyPI 安装
```bash
pip install cloudburst-fargate
```

### 从 GitHub 安装
```bash
pip install git+https://github.com/preangelleo/cloudburst-fargate.git
```

### 从源代码安装
```bash
git clone https://github.com/preangelleo/cloudburst-fargate.git
cd cloudburst-fargate
pip install -e .
```

## 🆚 CloudBurst 演进：EC2 → Fargate

| 功能特性 | CloudBurst EC2 (v1) | **CloudBurst Fargate (v2)** |
|---------|---------------------|------------------------------|
| **启动时间** | ~75 秒 | **~30 秒** ⚡ |
| **基础设施** | 管理 EC2 实例 | **完全无服务器** 🎯 |
| **并行处理** | 仅单实例 | **多个并发任务** 🔄 |
| **可用性** | 受配额限制 | **近 100% 可用** ✅ |
| **扩展性** | 受 EC2 容量限制 | **无限并发任务** 📈 |
| **计费模式** | 按分钟计费 | **按秒计费** 💰 |
| **闲置成本** | 遗忘实例的风险 | **零闲置成本** 🔥 |

## 🚀 快速开始

### 1. 安装包
```bash
pip install cloudburst-fargate
```

### 2. 设置 AWS 权限 (关键步骤)

CloudBurst Fargate 需要特定的 IAM 权限来管理 ECS 任务、访问 VPC 资源和处理容器操作。在设置过程中您需要**4 次添加权限**：

#### 所需的 IAM 权限
```json
{
  "Version": "2012-10-17", 
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:StopTask", 
        "ecs:DescribeTasks",
        "ecs:DescribeClusters",
        "ecs:ListTasks",
        "ecs:ListTagsForResource",
        "ecs:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeSubnets", 
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:DescribeVpcs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/ecs/cloudburst*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/ecsTaskExecutionRole"
    }
  ]
}
```

#### 逐步权限设置
1. **第一个权限**: ECS 任务管理
   ```bash
   # 添加 ECS 权限用于运行和管理 Fargate 任务
   aws iam attach-user-policy --user-name 你的用户名 --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
   ```

2. **第二个权限**: VPC 和网络访问
   ```bash
   # 添加 EC2 权限用于 VPC、子网和安全组
   aws iam attach-user-policy --user-name 你的用户名 --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess
   ```

3. **第三个权限**: CloudWatch 日志
   ```bash
   # 添加 CloudWatch 权限用于容器日志记录
   aws iam attach-user-policy --user-name 你的用户名 --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
   ```

4. **第四个权限**: IAM 角色传递
   ```bash
   # 添加权限以将执行角色传递给 ECS 任务
   aws iam put-user-policy --user-name 你的用户名 --policy-name ECSTaskRolePass --policy-document file://pass-role-policy.json
   ```

### 3. 环境配置
```bash
# 复制并自定义配置
cp .env.example .env

# 编辑 .env 文件，配置你的 AWS 凭证和 VPC 设置：
# - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (具备上述权限)
# - AWS_SUBNET_ID (你的 VPC 子网，需有互联网访问)
# - AWS_SECURITY_GROUP_ID (允许端口 5000 和出站 HTTPS)
```

### 4. 测试设置
```python
from cloudburst_fargate import FargateOperationV1

# 快速单场景测试
processor = FargateOperationV1(config_priority=1)
scenes = [{
    "scene_name": "test_scene",
    "image_path": "path/to/image.png",
    "audio_path": "path/to/audio.mp3",
    "subtitle_path": "path/to/subtitle.srt"  # 可选
}]

result = processor.execute_batch(scenes, language="chinese", enable_zoom=True)
print(f"✅ 生成了 {result['successful_scenes']} 个视频")
```

### 5. 并行处理（生产就绪！）
```python
from cloudburst_fargate.fargate_operation import execute_parallel_batches

# 跨多个并行 Fargate 容器处理多个场景
scenes = [
    {"scene_name": "场景_001", "image_path": "...", "audio_path": "..."},
    {"scene_name": "场景_002", "image_path": "...", "audio_path": "..."},
    {"scene_name": "场景_003", "image_path": "...", "audio_path": "..."},
    {"scene_name": "场景_004", "image_path": "...", "audio_path": "..."}
]

# 自动分配到 2 个并行任务（每个 2 个场景）
result = execute_parallel_batches(
    scenes=scenes,
    scenes_per_batch=2,        # 每个 Fargate 容器 2 个场景
    max_parallel_tasks=2,      # 2 个并发容器
    language="chinese",
    enable_zoom=True,
    config_priority=1,         # CPU 配置 (1-5, 默认: 4)
    watermark_path=None,       # 可选水印图像
    is_portrait=False,         # 竖屏模式 (默认: False)
    saving_dir="./output",     # 输出目录
    background_box=True,       # 字幕背景 (默认: True)
    background_opacity=0.2     # 背景透明度 0-1 (默认: 0.2)
)

print(f"🚀 效率提升: {result['efficiency']['speedup_factor']:.2f}x 加速")
print(f"💰 总成本: ${result['total_cost_usd']:.4f}")
print(f"📁 下载了 {len(result['downloaded_files'])} 个视频")
```

## ⚡ 并行处理架构

CloudBurst Fargate v2 引入了**真正的并行处理**：

### 架构优势
- **并发任务**：多个 Fargate 容器同时运行
- **智能分配**：场景自动分布到各个任务中
- **高效工作流**：每个任务处理场景 → 下载 → 终止
- **成本优化**：只为所有容器的实际处理时间付费

### 示例：4 个场景，2 个任务
```
任务 1: 启动 → 处理场景_001 → 下载 → 处理场景_002 → 下载 → 终止
任务 2: 启动 → 处理场景_003 → 下载 → 处理场景_004 → 下载 → 终止

结果：1.8x 加速，所有视频自动下载
```

## 📊 Fargate 配置选项

为你的工作负载选择合适的性能级别：

```python
# 经济型：1 vCPU, 2GB 内存 (~$0.044/小时) - 轻量工作负载
processor = FargateOperationV1(config_priority=5)

# 标准型：2 vCPU, 4GB 内存 (~$0.088/小时) - 最常见选择
processor = FargateOperationV1(config_priority=1)  # 默认

# 高性能：4 vCPU, 8GB 内存 (~$0.175/小时) - 重型场景
processor = FargateOperationV1(config_priority=2)

# 超高性能：8 vCPU, 16GB 内存 (~$0.351/小时) - 最大速度
processor = FargateOperationV1(config_priority=3)

# 最大性能：16 vCPU, 32GB 内存 (~$0.702/小时) - 企业级
processor = FargateOperationV1(config_priority=4)
```

## 🎬 完整示例（生产就绪）

参见 [`example_usage.py`](./example_usage.py) 获取全面示例，包括：
- 所有 CPU 配置选项
- 完整 API 参数参考
- 单场景处理
- 批处理示例
- 并行处理配置
- 成本优化策略

```python
# 快速并行处理示例
from cloudburst_fargate.fargate_operation import execute_parallel_batches

result = execute_parallel_batches(
    scenes=your_scenes,
    scenes_per_batch=3,          # 每容器场景数
    max_parallel_tasks=4,        # 并发容器数
    language="chinese",          # 或 "english"
    enable_zoom=True,            # 添加缩放效果
    config_priority=2,           # 高性能配置 (1-5)
    min_scenes_per_batch=5,      # 最少场景数 (默认: 5)
    watermark_path=None,         # 可选水印
    is_portrait=False,           # 竖屏视频模式
    saving_dir="./videos",       # 输出目录
    background_box=True,         # 显示字幕背景
    background_opacity=0.2       # 字幕透明度
)

# 自动结果：
# ✅ 所有视频处理并下载完成
# 💰 跨并行任务的最优成本分配
# 📈 详细的效率和时间指标
```

## 💡 核心优势

### 1. **真正无服务器与并行扩展**
- **按秒计费**，从容器启动到完成
- **多个并发容器**实现更快处理
- 无遗忘运行实例的风险
- 保证自动清理

### 2. **零基础设施管理**
- 无需监控 EC2 实例
- 无需 SSH 密钥或安全补丁
- AWS 处理所有基础设施和扩展

### 3. **生产级性能**
- **30秒启动** vs EC2 的 75+ 秒
- **并行处理**跨多个容器
- 智能场景分配和负载均衡
- 一致性能（无"邻居噪音"问题）

### 4. **企业就绪**
- 内置高可用和自动重试
- 与 AWS CloudWatch 日志集成
- VPC 网络支持
- 成本跟踪和优化

## 💰 成本对比

**示例：处理 8 个视频场景**

| 方法 | 配置 | 时间 | 成本 | 效率 |
|------|------|------|------|------|
| **顺序（单任务）** | 2 vCPU | 16 分钟 | $0.024 | 1.0x |
| **🏆 并行（4任务×2场景）** | 每个 2 vCPU | 9 分钟 | $0.026 | **1.8x 更快** |
| **24/7 GPU 服务器** | 常驻 | - | ~$500/月 | - |

**关键洞察**：成本仅增加 8%，时间却减少 80%！

## 🔧 高级功能

### 智能场景分配
框架自动：
- 将场景均匀分布到并行任务中
- 处理批次大小不能整除时的剩余场景
- 根据你的配置优化成本与速度的平衡

### 实时监控
```python
# 内置成本跟踪和性能指标
result = execute_parallel_batches(scenes=scenes, ...)

print(f"使用任务数: {result['tasks_used']}")
print(f"处理效率: {result['efficiency']['processing_efficiency']:.1f}%")
print(f"加速因子: {result['efficiency']['speedup_factor']:.2f}x")
print(f"每场景成本: ${result['total_cost_usd']/len(scenes):.4f}")
```

### 灵活配置
```python
# 环境变量或 .env 文件
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SUBNET_ID=subnet-xxxxxxxxx
AWS_SECURITY_GROUP_ID=sg-xxxxxxxxx
ECS_CLUSTER_NAME=cloudburst-cluster
ECS_TASK_DEFINITION=cloudburst-task
```

## 🛠️ 文件结构

清理后的项目结构：
```
cloudburst_fargate/
├── fargate_operation_v1.py    # 核心 Fargate 操作和并行处理
├── example_usage.py           # 完整使用示例和 API 参考
├── README.md                  # 英文文档
├── README_CN.md              # 本文件（中文文档）
├── requirements.txt          # Python 依赖
├── .env.example             # 环境变量模板
├── Docs/                    # 技术文档
└── backup_test_files/       # 测试文件（Git 忽略）
```

## 🔧 故障排除

### 常见问题

**任务启动失败：**
- 检查 .env 文件中的子网和安全组 ID
- 确保子网有互联网访问（公有子网或 NAT 网关）
- 验证 AWS 凭证具有正确权限

**网络错误：**
- 安全组必须允许出站 HTTPS（端口 443）用于 Docker 拉取
- 安全组必须允许入站 TCP 端口 5000 用于 API 访问

**权限错误：**
- 验证 AWS 凭证：`aws sts get-caller-identity`
- 需要的 IAM 权限：ECS、ECR、CloudWatch、EC2（用于 VPC）

### 调试模式
```python
# 启用详细的 AWS 日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 或检查 CloudWatch 日志：/ecs/cloudburst
```

### 任务监控与管理（v2 新功能）
CloudBurst Fargate 现在包含高级任务监控和清理功能，确保生产环境的可靠运行：

#### 列出运行中的任务
```python
from cloudburst_fargate import FargateOperationV1

# 初始化操作
fargate_op = FargateOperationV1()

# 列出所有由 animagent 创建的运行中的 Fargate 任务
running_tasks = fargate_op.list_running_tasks(filter_animagent_only=True)

for task in running_tasks:
    print(f"任务: {task['task_arn']}")
    print(f"状态: {task['status']}")
    print(f"启动时间: {task['started_at']}")
    print(f"公网 IP: {task['public_ip']}")
    print(f"标签: {task['tags']}")
```

#### 清理过期任务
```python
# 清理所有 animagent 创建的任务（双重安全机制）
cleanup_result = fargate_op.cleanup_all_tasks(
    reason="定期清理",
    filter_animagent_only=True  # 只清理标记为 CreatedBy=animagent 的任务
)

print(f"清理结果: {cleanup_result['message']}")
print(f"已终止任务数: {cleanup_result['terminated_count']}")
print(f"清理失败数: {cleanup_result['failed_count']}")
```

#### 任务标识
CloudBurst Fargate 创建的所有任务都会自动添加标签以便识别：
- `CreatedBy`: `animagent` - 标识此框架创建的任务
- `Purpose`: `video-generation` - 标记任务用途
- `Scene`: 正在处理的场景名称
- `Language`: 处理语言（english/chinese）

这个标签系统确保清理操作只影响您的应用程序创建的任务，防止干扰同一 ECS 集群中其他服务的任务。

## 🎯 发展路线

- [x] **✅ 并行处理**：多个并发 Fargate 任务
- [ ] **Fargate Spot**：为非关键工作负载节省 70% 成本
- [ ] **自动扩展**：基于队列大小的动态资源分配
- [ ] **S3 集成**：无需本地下载的直接文件传输
- [ ] **Webhook 支持**：处理完成时的实时通知
- [ ] **GPU 支持**：用于 AI 密集型工作负载的 Fargate GPU 实例

## 🔗 基于视频生成 API

本项目基于我的第一个开源项目：[**视频生成 API**](https://github.com/preangelleo/video-generation-docker)

### 完美组合：
- **[视频生成 API](https://github.com/preangelleo/video-generation-docker)**：实际生成视频的核心 Docker 镜像
- **CloudBurst Fargate（本项目）**：自动化 AWS Fargate 部署，按需运行 API

### 两种部署选择：
| 选项 | 适用场景 | 成本模式 | 设置方式 |
|------|---------|---------|----------|
| **视频生成 API** | 频繁使用，常驻服务 | 按月付费（~$500） | 24/7 运行 Docker 容器 |
| **CloudBurst Fargate** | 偶尔使用，批量处理 | 按秒付费（~$0.026/批） | 自动创建/销毁容器 |

CloudBurst Fargate 自动拉取并部署视频生成 API Docker 镜像，让您以 95%+ 的成本节省获得同样强大的视频生成能力！

## 📚 API 参考：execute_parallel_batches()

### 完整参数列表

```python
execute_parallel_batches(
    scenes: List[Dict],              # 必需：场景字典列表
    scenes_per_batch: int = 10,      # 每个 Fargate 容器的场景数
    max_parallel_tasks: int = 10,    # 最大并发容器数
    language: str = "chinese",       # 语言："chinese" 或 "english"
    enable_zoom: bool = True,        # 启用缩放进出效果
    config_priority: int = 4,        # CPU 配置 (1-5，见下表)
    min_scenes_per_batch: int = 5,   # 启动容器的最少场景数
    watermark_path: str = None,      # 可选水印图像路径
    is_portrait: bool = False,       # 竖屏视频模式
    saving_dir: str = None,          # 输出目录 (默认: ./cloudburst_fargate_results/)
    background_box: bool = True,     # 显示字幕背景
    background_opacity: float = 0.2  # 背景透明度 (0=不透明，1=完全透明)
) -> Dict
```

### 场景字典格式

`scenes` 列表中的每个场景必须包含：

```python
{
    "scene_name": "unique_name",     # 必需：场景的唯一标识符
    "image_path": "path/to/image",   # 必需：图像文件路径
    "audio_path": "path/to/audio",   # 必需：音频文件路径
    "subtitle_path": "path/to/srt"   # 可选：字幕文件路径
}
```

### CPU 配置优先级

| 优先级 | vCPU | 内存 | 名称 | 每小时成本 | 最适合 |
|--------|------|------|------|------------|--------|
| 1 | 2 | 4GB | 标准 | $0.088 | 大多数任务 |
| 2 | 4 | 8GB | 高性能 | $0.175 | 更快处理 |
| 3 | 8 | 16GB | 超高性能 | $0.351 | 非常快 |
| 4 | 16 | 32GB | 最高性能 | $0.702 | 最快 (默认) |
| 5 | 1 | 2GB | 经济 | $0.044 | 成本敏感 |

### 返回值结构

```python
{
    "success": bool,                    # 总体成功状态
    "total_scenes": int,                # 输入场景总数
    "successful_scenes": int,           # 成功处理的场景数
    "failed_scenes": int,               # 失败的场景数
    "total_cost_usd": float,            # 总成本（美元）
    "total_duration": float,            # 总时间（秒）
    "downloaded_files": List[str],      # 下载的视频路径
    "task_results": List[Dict],         # 各个任务的结果
    "tasks_used": int,                  # 使用的 Fargate 任务数
    "efficiency": {
        "speedup_factor": float,        # 相比顺序处理的加速倍数
        "processing_efficiency": float,  # 处理时间占比百分比
        "cost_per_scene": float         # 每个场景的平均成本
    }
}
```

### 智能分配示例

```python
# 示例 1：均匀分配
# 50 个场景，batch=10，max_tasks=10 → 5 个任务 × 每个 10 个场景

# 示例 2：为效率重新分配
# 120 个场景，batch=10，max_tasks=10 → 10 个任务 × 每个 12 个场景

# 示例 3：处理余数
# 101 个场景，batch=10，max_tasks=10 → 9 个任务 × 10 个场景 + 1 个任务 × 11 个场景
```

## 📄 许可证

MIT 许可证 - 与原始 CloudBurst 项目相同

---

**从单任务处理到并行无服务器规模 - CloudBurst Fargate 已为生产环境准备就绪！** 🚀

*停止管理基础设施，开始大规模处理视频。*