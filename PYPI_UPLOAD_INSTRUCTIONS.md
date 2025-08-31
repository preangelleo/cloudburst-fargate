# 📦 CloudBurst Fargate - PyPI 上传指南

CloudBurst Fargate 包已经准备好上传到 PyPI！

## ✅ 已完成的准备工作

1. **包结构创建完成**
   - setup.py 和 pyproject.toml 配置完整
   - 版本号: 1.0.0
   - 作者: Leo Wang (me@leowang.net)
   - MIT License

2. **发布包已构建**
   - `dist/cloudburst_fargate-1.0.0-py3-none-any.whl` (23.6 KB)
   - `dist/cloudburst_fargate-1.0.0.tar.gz` (79.5 KB)

3. **本地测试通过**
   - 包可以正确安装
   - 所有功能正常工作

## 🚀 上传到 PyPI 的步骤

### 1. 获取 PyPI API Token

1. 登录 PyPI: https://pypi.org/account/login/
2. 进入账户设置: https://pypi.org/manage/account/
3. 滚动到 "API tokens" 部分
4. 点击 "Add API token"
5. 设置 Token 名称 (例如: "cloudburst-fargate-upload")
6. 选择范围: "Entire account" 或特定项目
7. 复制生成的 token (以 `pypi-` 开头)

### 2. 设置环境变量

```bash
export PYPI_API_TOKEN='pypi-你的token在这里'
```

### 3. 执行上传

```bash
# 方式 1: 使用准备好的脚本
python upload_to_pypi.py

# 方式 2: 直接使用 twine
python -m twine upload dist/* --username __token__ --password $PYPI_API_TOKEN
```

### 4. 验证上传

上传成功后，访问: https://pypi.org/project/cloudburst-fargate/

## 📝 后续用户安装方式

```bash
# 从 PyPI 安装
pip install cloudburst-fargate

# 从 GitHub 安装 (当前可用)
pip install git+https://github.com/preangelleo/cloudburst-fargate.git
```

## ⚠️ 注意事项

1. 首次上传需要确保包名 `cloudburst-fargate` 在 PyPI 上未被占用
2. 如果需要更新版本，记得修改 `cloudburst_fargate/version.py` 中的版本号
3. 每次更新后需要重新构建: `python -m build`

## 🔧 故障排除

如果遇到 403 错误:
- 检查 token 是否正确复制（包括 `pypi-` 前缀）
- 确保 token 有正确的权限
- 检查包名是否已被占用

---

准备就绪！设置好 PYPI_API_TOKEN 后即可上传。🎉