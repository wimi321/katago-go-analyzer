#!/usr/bin/env python3
"""
围棋棋盘检测模块 - 优化版
改进：
1. 更精确的角点估计
2. 更好的网格映射
3. NMS去重
"""

import cv2
import numpy as np
from collections import defaultdict
from ultralytics import YOLO


class GoBoardDetector:
    """优化的围棋棋盘检测器"""
    
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.board_size = 19
        print(f"✅ 模型加载: {model_path}")
        print(f"   类别: {self.model.names}")
    
    def detect(self, image_path, conf_threshold=0.25):
        """检测所有目标"""
        results = self.model(image_path, conf=conf_threshold, iou=0.7)[0]
        
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls = int(box.cls[0].cpu().numpy())
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            w, h = x2 - x1, y2 - y1
            
            detections.append({
                'class': cls,
                'conf': conf,
                'center': [cx, cy],
                'bbox': [x1, y1, w, h],
                'size': (w + h) / 2
            })
        
        return detections
    
    def nms_merge(self, detections, iou_threshold=0.5):
        """NMS合并重叠检测"""
        if not detections:
            return []
        
        # 按置信度排序
        detections = sorted(detections, key=lambda x: x['conf'], reverse=True)
        
        keep = []
        while detections:
            # 取置信度最高的
            best = detections.pop(0)
            keep.append(best)
            
            # 移除重叠度高的
            remaining = []
            for d in detections:
                iou = self.calculate_iou(best['bbox'], d['bbox'])
                if iou < iou_threshold:
                    remaining.append(d)
            detections = remaining
        
        return keep
    
    def calculate_iou(self, box1, box2):
        """计算IoU"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[0] + box1[2], box2[0] + box2[2])
        y2 = min(box1[1] + box1[3], box2[1] + box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        box1_area = box1[2] * box1[3]
        box2_area = box2[2] * box2[3]
        
        return inter_area / (box1_area + box2_area - inter_area + 1e-6)
    
    def estimate_corners_from_stones(self, stones):
        """从棋子位置估计棋盘角点"""
        if len(stones) < 4:
            return None, None
        
        xs = [s['center'][0] for s in stones]
        ys = [s['center'][1] for s in stones]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # 计算格子大小
        board_width = max_x - min_x
        board_height = max_y - min_y
        cell_size = max(board_width, board_height) / 18
        
        # 计算边距
        margin = cell_size * 0.5
        
        corners = {
            'top_left': [min_x - margin, min_y - margin],
            'top_right': [max_x + margin, min_y - margin],
            'bottom_left': [min_x - margin, max_y + margin],
            'bottom_right': [max_x + margin, max_y + margin]
        }
        
        return corners, cell_size
    
    def map_to_grid(self, stones, corners, cell_size):
        """将棋子映射到19x19网格"""
        if corners is None:
            return {}
        
        grid = defaultdict(list)
        
        # 计算变换
        # 从棋盘坐标到网格坐标
        board_min_x = corners['top_left'][0]
        board_min_y = corners['bottom_left'][1]  # 注意Y轴方向
        
        for stone in stones:
            cx, cy = stone['center']
            
            # 投影到网格坐标
            col = int((cx - board_min_x) / cell_size)
            row = int((board_min_y - cy) / cell_size)  # 翻转Y轴
            
            # 边界检查
            if 0 <= row < self.board_size and 0 <= col < self.board_size:
                color = 'b' if stone['class'] == 0 else 'w'
                grid[(row, col)].append({
                    'color': color,
                    'conf': stone['conf']
                })
        
        return grid
    
    def merge_overlapping(self, grid):
        """合并重叠检测"""
        merged = {}
        for (row, col), stones in grid.items():
            if len(stones) == 1:
                merged[(row, col)] = stones[0]
            else:
                # 同一位置多个检测：按颜色多数投票
                black_votes = sum(1 for s in stones if s['color'] == 'b')
                white_votes = len(stones) - black_votes
                
                best = max(stones, key=lambda x: x['conf'])
                best['color'] = 'b' if black_votes > white_votes else 'w'
                merged[(row, col)] = best
        
        return merged
    
    def generate_sgf(self, grid):
        """生成SGF格式"""
        sgf = """(;FF[4]CA[UTF-8]SZ[19]
KM[6.5]
PB[Black]
PW[White]
DT[2026-02-06]
RE[Unknown]
"""
        
        # 按位置排序
        sorted_positions = sorted(grid.keys(), key=lambda x: (x[0], x[1]))
        
        for pos in sorted_positions:
            stone = grid[pos]
            row, col = pos
            sgf_col = chr(ord('a') + col)
            sgf_row = chr(ord('a') + row)
            color_letter = 'B' if stone['color'] == 'b' else 'W'
            sgf += f"{color_letter}[{sgf_col}{sgf_row}]\n"
        
        sgf += ")"
        return sgf
    
    def process_image(self, image_path, output_sgf=None):
        """处理图片"""
        print(f"\n📷 检测: {image_path}")
        
        # Step 1: 检测
        detections = self.detect(image_path, conf_threshold=0.15)
        print(f"   原始检测: {len(detections)} 个")
        
        # Step 2: NMS去重
        detections = self.nms_merge(detections, iou_threshold=0.3)
        print(f"   NMS后: {len(detections)} 个")
        
        # 分类统计
        black = sum(1 for d in detections if d['class'] == 0)
        white = sum(1 for d in detections if d['class'] == 1)
        corners_found = sum(1 for d in detections if d['class'] == 2)
        print(f"   黑子: {black}, 白子: {white}, 角点: {corners_found}")
        
        # Step 3: 分离棋子并估计角点
        stones = [d for d in detections if d['class'] in [0, 1]]
        corners_dict, cell_size = self.estimate_corners_from_stones(stones)
        
        if corners_dict:
            print(f"   ✓ 角点估计 (cell={cell_size:.1f})")
        else:
            print("   ⚠️ 无法估计角点")
        
        # Step 4: 映射到网格
        if corners_dict and cell_size:
            grid = self.map_to_grid(stones, corners_dict, cell_size)
            grid = self.merge_overlapping(grid)
            print(f"   ✓ 网格位置: {len(grid)}")
        else:
            grid = {}
        
        # Step 5: 生成SGF
        sgf_content = self.generate_sgf(grid)
        
        if output_sgf:
            with open(output_sgf, 'w') as f:
                f.write(sgf_content)
            print(f"   ✓ SGF保存: {output_sgf}")
        
        stats = {
            'black': sum(1 for s in grid.values() if s['color'] == 'b'),
            'white': sum(1 for s in grid.values() if s['color'] == 'w'),
            'total': len(grid),
            'cell_size': cell_size
        }
        
        return sgf_content, stats


if __name__ == "__main__":
    import sys
    import os
    
    detector = GoBoardDetector("/Users/haoc/.openclaw/workspace/runs/detect/runs/go_board_yolo26/exp/weights/best.pt")
    
    if len(sys.argv) > 1:
        sgf, stats = detector.process_image(sys.argv[1])
        print(f"\n结果: {stats}")
    else:
        # 默认测试
        test_img = "/Users/haoc/.openclaw/workspace/merged_dataset/valid/images/0b24b67a3b0a4db1afe841a1acdb1867_jpg.rf.6919d0af4668f6af5b2b0ddd53832e0a.jpg"
        if os.path.exists(test_img):
            sgf, stats = detector.process_image(test_img, "/Users/haoc/.openclaw/workspace/test_v3.sgf")
            print(f"\n✅ 测试完成: {stats}")
