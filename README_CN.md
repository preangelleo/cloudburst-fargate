# CloudBurst - 按需云端视频生成框架

我的第二个开源项目！🚀

[English Version](./README.md)

## 这是什么？

一个 **自动管理 AWS EC2 实例** 的 Python 框架，专门用于按需视频生成任务。

**核心价值**：当你的应用需要生成视频时（使用我们的 [视频生成 API](https://github.com/betashow/video-generation-docker)），这个框架会：
- 🚀 启动一个带有视频生成 Docker 容器的 EC2 实例
- 🎬 并行处理你的视频生成请求
- 📥 下载完成的视频
- 🛑 立即终止实例以节省成本
- 💰 你只需为实际处理时间付费（按分钟计费，而不是按月！）

**适用场景**：需要在工作流程中生成视频，但不想维护 24/7 GPU 实例的生产应用。

## 🔗 相关项目

本项目基于我的第一个开源项目：[**视频生成 API**](https://github.com/betashow/video-generation-docker)

- **视频生成 API**：运行持久的 Docker 容器进行视频生成（按月付费）
- **本项目**：按需创建，随时可用；用完即关，按秒计费

根据你的需求选择：
- 频繁使用 → 使用视频生成 API（持久容器）
- 偶尔使用 → 使用本框架（按需创建，随时可用；用完即关，按秒计费）

## 🎯 解决的问题

24/7 运行云实例太贵了。这个框架：
- ✅ 仅在需要时创建实例
- ✅ 运行你的任务（如视频生成）
- ✅ 下载结果
- ✅ 自动终止实例
- ✅ 显示准确成本（例如：15个视频仅需 $0.018）

**按分钟付费，而不是按月！**

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/preangelleo/cloudburst
cd cloudburst
pip install -r requirements.txt
```

### 2. 配置

创建 `.env` 文件：
```env
# AWS 设置
AWS_REGION=us-east-1
AWS_KEY_PAIR_NAME=your-keypair-name
AWS_SECURITY_GROUP_ID=sg-xxxxxxxxx
AWS_SUBNET_ID=subnet-xxxxxxxxx

# 可选：指定 AMI 或实例类型
AWS_INSTANCE_TYPE=c5.2xlarge
DOCKER_IMAGE=betashow/video-generation-api:latest
```

### 3. 使用示例

```python
from instant_instance_operation_v2 import scan_and_test_folder

# 处理整个文件夹的视频
result = scan_and_test_folder(
    folder_path="./video_scenes/",
    language="chinese",
    enable_zoom=True
)

print(f"✅ 生成了 {result['successful_scenes']} 个视频")
print(f"💰 总成本：${result['cost_usd']:.4f}")
print(f"⏱️  总时间：{result['total_time']:.1f} 秒")
```

## 📊 真实案例

生成 15 个带特效的视频：
- ✅ 成功生成 15 个视频
- 💰 总成本：$0.0187
- ⏱️ 总时间：385.2 秒

**对比传统方式**：
- 24/7 GPU 实例：~$500/月
- 使用 CloudBurst：~$0.02/批次

## 💡 主要特性

### 1. **智能实例管理**
- 自动回退到备用实例类型
- 优雅处理 AWS 配额限制
- 支持竞价实例（即将推出）

### 2. **实时成本追踪**
- 使用 AWS Pricing API 获取准确成本
- 精确到秒的运行时间追踪
- 返回简单的浮点数便于计费

### 3. **为自动化而生**
- 干净的 Python 字典返回格式
- 为数据库存储准备就绪
- 完美适配 CI/CD 流水线

### 4. **生产就绪**
- 全面的错误处理
- 失败时自动清理
- 详细的进度日志

## 📈 使用场景

- **🎬 视频/音频处理** - 在 GPU 实例上处理媒体文件
- **🤖 机器学习模型训练** - 无需 24/7 GPU 成本即可训练模型
- **📊 数据处理** - 按需运行大数据任务
- **🧪 测试与 CI/CD** - 自动创建测试环境
- **🎨 渲染** - 3D 渲染、图像处理

## 🛠️ 高级配置

### 实例优先级（自动回退）
```python
# 在 __init__ 方法中配置
self.instance_configs = [
    {
        "priority": 1,
        "instance_type": "c5.2xlarge",   # CPU 优化型
        "description": "计算优化 - 8 vCPU, 16GB RAM"
    },
    {
        "priority": 2, 
        "instance_type": "m5.xlarge",    # 内存优化型
        "description": "内存优化 - 4 vCPU, 16GB RAM"
    },
    {
        "priority": 3,
        "instance_type": "g4dn.xlarge",  # GPU 用于 ML/视频
        "description": "NVIDIA T4 - 4 vCPU, 16GB RAM, 16GB GPU"
    }
]
```

### 文件夹结构要求
```
你的场景文件夹/
├── images/
│   ├── scene_001.png
│   ├── scene_002.png
├── audio/
│   ├── scene_001.mp3
│   ├── scene_002.mp3
└── subtitle/ (可选)
    ├── scene_001.srt
    ├── scene_002.srt
```

## 📋 系统要求

- Python 3.7+
- AWS 账户（需要 EC2 权限）
- boto3, requests, python-dotenv

## 🤝 贡献

这是我的第二个开源项目！欢迎：
- 报告 bug
- 建议新功能
- 提交 PR
- 如果觉得有用，请给个 Star！⭐

## 📊 真实生产环境基准测试

基于 AWS EC2 c5.2xlarge 实例的实际生产测试数据：

### 视频生成性能
- **工作负载**：15 个场景（4 种不同场景类型）
- **总运行时间**：~25 分钟
- **总成本**：$0.20 美元
- **实例启动时间**：~2 分钟（从启动到就绪）
- **处理结果**：生成 60 个视频
- **成功率**：100%

### 成本明细
```
实例启动和设置：~2 分钟
视频处理：~23 分钟  
实例终止：<1 分钟
--------------------------------
总时间：25 分钟
总成本：$0.20（@ $0.475/小时）
```

### 场景性能对比
| 场景类型 | 视频数 | 平均时间/视频 | 总时间 | 文件大小 |
|----------|--------|---------------|--------|----------|
| 基础版 | 15 | 6.5秒 | 2.2 分钟 | ~0.8MB/个 |
| 仅字幕 | 15 | 6.7秒 | 2.4 分钟 | ~0.8MB/个 |
| 仅特效 | 15 | 34.0秒 | 9.3 分钟 | ~3.5MB/个 |
| 完整版 | 15 | 34.5秒 | 9.6 分钟 | ~3.5MB/个 |

### 💡 成本对比
- **传统 24/7 GPU 实例**：~$500/月
- **CloudBurst（100 批次/月）**：~$20/月
- **节省**：96% 成本降低！

**真正的"即插即用"体验**：从零到 60 个视频，仅需 25 分钟，只花 $0.20！

## 📄 许可证

MIT License

---

**停止为闲置的云实例付费 - 仅在需要时使用它们！**

🎉 感谢使用 CloudBurst！如有问题，欢迎在 [Issues](https://github.com/preangelleo/cloudburst/issues) 中提出。