# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## 🛠️ 已配置技能

### 已启用的技能
- **weather** 🌤️ - 天气查询（无需API Key）
- **healthcheck** 🔒 - 系统安全检查
- **github** 🐙 - GitHub 操作
- **bird** 🐦 - X/Twitter 操作

### 使用方式
在对话中直接说：
- "查一下北京天气"
- "帮我检查系统安全"
- "搜索 GitHub 仓库 xxx"

## 🤖 YOLO 训练项目

### 脚本位置
- `/Users/haoc/.openclaw/workspace/01_merge_datasets.py` - 数据集融合
- `/Users/haoc/.openclaw/workspace/02_train_model.py` - 模型训练
- `/Users/haoc/.openclaw/workspace/03_inference_sgf.py` - 推理与SGF生成

### 运行前提
1. 设置 Roboflow API Key（在01_merge_datasets.py中）
2. 安装依赖：`pip install ultralytics roboflow opencv-python numpy`

### 注意事项
- 训练使用 MPS（Mac GPU 加速）
- 输入图片尺寸：1024
- 训练轮数：50 epochs

## 🏮 KataGo 分析引擎

### 组件
- **分析器**: `/Users/haoc/.openclaw/workspace/katago_analyzer.py`
- **文档**: `/Users/haoc/.openclaw/workspace/KATAGO_README.md`
- **模型**: `~/.katago/models/kata1-b28c512nbt-s12374138624-d5703190512.bin.gz`
- **配置**: `/tmp/katago.cfg` (来自 KataGo 示例)

### 规格
- 版本: KataGo v1.16.4
- 模型: b28c512nbt (~10B 参数, 259MB)
- 后端: Metal (Apple M4 Pro)
- 协议: GTP v2 + kata-analyze (JSON输出)

### 核心命令
```bash
# 启动分析
katago gtp -config /tmp/katago.cfg -model ~/.katago/models/kata1-b28c512nbt-s12374138624-d5703190512.bin.gz

# Python 使用
python3 /Users/haoc/.openclaw/workspace/katago_analyzer.py
```

### Python API
```python
from katago_analyzer import KataGoAnalyzer, Color

analyzer = KataGoAnalyzer(model_path="...")
analyzer.start()
results = analyzer.analyze(Color.WHITE, visits=200)
analyzer.stop()
```
