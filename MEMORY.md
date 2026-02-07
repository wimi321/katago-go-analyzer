# MEMORY.md

## YOLO26 围棋项目 (2025-01-24)

### 训练状态
- **进度**: Epoch 11/50, mAP50=0.958
- **预计完成**: ~20分钟
- **位置**: `runs/go_board_yolo26/exp/`

### 数据集
- 合并自两个Roboflow数据集
- 772训练图 / 21验证图
- Class mapping: black=0, white=1, corner=2

### 脚本
- 训练: `02_train_model.py`
- 推理: `03_inference_sgf.py` (SGF格式输出)
