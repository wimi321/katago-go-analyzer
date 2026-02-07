# 待办任务清单 📋

> 每次问"要做什么"时，查看此文件

---

## 🚀 YOLO 训练项目（进行中）

### 第1步：重启 OpenClaw
```bash
openclaw gateway restart
```
- 目的：让已启用的技能生效（天气、健康检查、GitHub、Twitter）

### 第2步：配置 Roboflow API Key
```bash
nano ~/.openclaw/workspace/01_merge_datasets.py
```
- 找到：`API_KEY = "YOUR_ROBOFLOW_API_KEY"`
- 替换：填入你的 Roboflow API Key
- 获取：https://app.roboflow.com/settings/api

### 第3步：安装 Python 依赖
```bash
pip install ultralytics roboflow opencv-python numpy
```

### 第4步：运行数据集融合
```bash
python ~/.openclaw/workspace/01_merge_datasets.py
```
- 输出：`~/.openclaw/workspace/merged_dataset/`

### 第5步：训练模型
```bash
python ~/.openclaw/workspace/02_train_model.py
```
- 使用：MPS（Mac GPU 加速）
- 预计耗时：几小时
- 输出：`~/.openclaw/workspace/runs/go_board_detection/weights/best.pt`

### 第6步：测试推理
```bash
python ~/.openclaw/workspace/03_inference_sgf.py
```
- 需要：准备一张棋盘图片放到 workspace

---

## 📌 快速参考

| 命令 | 说明 |
|------|------|
| `openclaw gateway restart` | 重启服务 |
| `openclaw status` | 查看状态 |
| `openclaw gateway --help` | 帮助 |

---

*创建时间：2026-02-06*
*最后更新：2026-02-06*
