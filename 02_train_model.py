#!/usr/bin/env python3
"""
YOLO26 训练脚本 - 直接使用 ultralytics
"""

from ultralytics import YOLO
import torch

def main():
    """训练 YOLO26 模型"""
    
    print("="*60)
    print("YOLO26 训练脚本")
    print("="*60)
    
    # 检查设备
    if torch.backends.mps.is_available():
        device = 'mps'
        print(f"✅ 使用 MPS (Apple Silicon GPU)")
    else:
        device = 'cpu'
        print("⚠️ MPS 不可用，使用 CPU")
    
    # 检查是否有预训练权重
    import os
    weights_path = 'yolo26n.pt'
    if not os.path.exists(weights_path):
        print(f"\n📥 下载 yolo26n.pt 预训练权重...")
        # ultralytics 会自动下载
        pass
    
    # 加载模型
    print(f"\n📦 加载模型...")
    model = YOLO('yolo26n.pt')
    print(f"模型: {model.model_name}")
    
    # 训练配置
    print(f"\n🏋️ 开始训练...")
    results = model.train(
        data='merged_dataset/merged_data.yaml',  # 数据集路径
        epochs=50,
        imgsz=1024,
        device=device,
        batch=8,
        workers=4,
        project='runs/go_board_yolo26',
        name='exp',
        exist_ok=True,
        optimizer='auto',
        verbose=True,
        save_period=10,
    )
    
    print(f"\n✅ 训练完成!")
    print(f"📁 结果保存: {results.save_dir}")
    
    # 验证
    print(f"\n📊 验证模型...")
    metrics = model.val()
    print(f"  mAP50: {metrics.box.map50:.4f}")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    
    return model, results


if __name__ == "__main__":
    main()
