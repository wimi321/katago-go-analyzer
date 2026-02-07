#!/usr/bin/env python3
"""
数据集下载脚本 - 使用 Roboflow API
"""

import os
import shutil
import yaml
import requests
from pathlib import Path
from zipfile import ZipFile
from tqdm import tqdm

# ============ 配置 ============
WORKSPACE = Path("/Users/haoc/.openclaw/workspace")
DATA_DIR = WORKSPACE / "merged_dataset"
API_KEY = "wNN4frQMDFeoT3rceijJ"

# 数据集配置
DATASETS = [
    {
        "name": "go-board-corners",
        "api_path": "test-pfq3c/go-board-4kjuw",
        "version": 1,
        "type": "corners",
        "class_map": {"corner": 2}
    },
    {
        "name": "stone-detection",
        "api_path": "hubbleunit/stone-detection-k4yeu",
        "version": 1,
        "type": "stones",
        "class_map": {"black": 0, "white": 1}
    }
]


def download_dataset(dataset_info):
    """使用 Roboflow API 下载数据集"""
    name = dataset_info["name"]
    api_path = dataset_info["api_path"]
    version = dataset_info["version"]
    
    print(f"\n{'='*50}")
    print(f"下载数据集: {name}")
    print(f"{'='*50}")
    
    # API URL
    url = f"https://api.roboflow.com/{api_path}/{version}/download"
    params = {
        "api_key": API_KEY,
        "format": "yolov8"
    }
    
    # 下载
    print(f"  正在下载...")
    response = requests.get(url, params=params, stream=True)
    
    if response.status_code != 200:
        print(f"  下载失败: {response.status_code}")
        print(f"  响应: {response.text[:500]}")
        return None
    
    # 保存 zip 文件
    zip_path = DATA_DIR / f"{name}.zip"
    total_size = int(response.headers.get('content-length', 0))
    
    with open(zip_path, 'wb') as f:
        for chunk in tqdm(response.iter_content(chunk_size=8192), total=total_size/8192, desc="  "):
            f.write(chunk)
    
    print(f"  下载完成: {zip_path}")
    
    # 解压
    print(f"  正在解压...")
    extract_dir = DATA_DIR / name
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    print(f"  解压完成: {extract_dir}")
    
    # 删除 zip
    zip_path.unlink()
    
    return extract_dir


def remap_labels(src_dir, dataset_info):
    """重新映射标签文件中的类别ID"""
    type_name = dataset_info["type"]
    class_map = dataset_info["class_map"]
    
    print(f"  重新映射标签: {type_name}")
    
    for split in ["train", "valid", "test"]:
        lbl_dir = src_dir / split / "labels"
        if not lbl_dir.exists():
            continue
        
        # 确定原始类别顺序
        if type_name == "corners":
            orig_classes = ["corner"]
        else:  # stones
            orig_classes = ["black", "white"]
        
        # 处理每个标签文件
        for lbl_file in lbl_dir.glob("*.txt"):
            lines = []
            with open(lbl_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    
                    orig_id = int(parts[0])
                    if orig_id < len(orig_classes):
                        new_id = class_map[orig_classes[orig_id]]
                        parts[0] = str(new_id)
                    
                    lines.append(" ".join(parts))
            
            with open(lbl_file, 'w') as f:
                f.write("\n".join(lines))
    
    print(f"  标签映射完成")


def merge_dataset_parts(src_dir, dst_dir, split):
    """合并数据集"""
    src_images = src_dir / split / "images"
    src_labels = src_dir / split / "labels"
    
    if not src_images.exists():
        return 0
    
    dst_images = dst_dir / "images" / split
    dst_labels = dst_dir / "labels" / split
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)
    
    # 复制图片
    img_count = 0
    for img_file in src_images.glob("*"):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            shutil.copy2(img_file, dst_images / img_file.name)
            img_count += 1
    
    # 复制标签
    for lbl_file in src_labels.glob("*.txt"):
        shutil.copy2(lbl_file, dst_labels / lbl_file.name)
    
    return img_count


def create_yaml_config(data_dir):
    """生成配置文件"""
    config = {
        "path": str(data_dir),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "names": {
            0: "black",
            1: "white",
            2: "corner"
        },
        "nc": 3
    }
    
    yaml_path = data_dir / "merged_data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"\n创建配置文件: {yaml_path}")


def verify_dataset(data_dir):
    """验证数据集"""
    print(f"\n验证数据集: {data_dir}")
    
    total = 0
    for split in ["train", "valid", "test"]:
        img_dir = data_dir / "images" / split
        if img_dir.exists():
            count = len(list(img_dir.glob("*.jpg")))
            total += count
            print(f"  {split}: {count} 张图片")
    
    return total


def main():
    """主函数"""
    print("="*60)
    print("数据集下载与融合脚本")
    print("="*60)
    
    # 清理目录
    if DATA_DIR.exists():
        print(f"清理目录: {DATA_DIR}")
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 下载并处理每个数据集
    for ds_info in DATASETS:
        src_dir = download_dataset(ds_info)
        if src_dir:
            remap_labels(src_dir, ds_info)
        else:
            print(f"  跳过 {ds_info['name']}")
    
    # 合并到统一目录
    print(f"\n合并数据集...")
    for ds_info in DATASETS:
        src_dir = DATA_DIR / ds_info["name"]
        if not src_dir.exists():
            continue
        
        for split in ["train", "valid", "test"]:
            count = merge_dataset_parts(src_dir, DATA_DIR, split)
            if count > 0:
                print(f"  {ds_info['name']}/{split}: {count} 张图片")
    
    # 清理临时目录
    for ds_info in DATASETS:
        tmp_dir = DATA_DIR / ds_info["name"]
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
    
    # 生成配置
    create_yaml_config(DATA_DIR)
    
    # 验证
    total = verify_dataset(DATA_DIR)
    
    print(f"\n" + "="*60)
    if total > 0:
        print(f"✅ 数据集融合完成! 共 {total} 张图片")
    else:
        print(f"❌ 未找到图片，请检查下载是否成功")
    print("="*60)


if __name__ == "__main__":
    main()
