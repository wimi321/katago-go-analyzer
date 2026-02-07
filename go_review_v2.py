#!/usr/bin/env python3
"""
围棋AI复盘系统 - 最终版
- YOLO检测 + 网格映射
- Katago分析 (20B模型)
- LLM复盘
"""

import os
import sys
import json
import subprocess
from collections import defaultdict
from ultralytics import YOLO


class GoReviewSystem:
    """围棋复盘系统"""
    
    def __init__(self):
        self.model_path = "/Users/haoc/.openclaw/workspace/runs/detect/runs/go_board_yolo26/exp/weights/best.pt"
        self.katago_bin = "/opt/homebrew/bin/katago"
        self.katago_model = "/Users/haoc/.openclaw/workspace/katago_model.bin.gz"
        self.katago_config = "/opt/homebrew/share/katago/configs/gtp_example.cfg"
        
        print("🔧 加载模型...")
        self.model = YOLO(self.model_path)
        print(f"✅ YOLO: {self.model_path}")
        print(f"   类别: {self.model.names}")
        
        # 检查Katago
        if os.path.exists(self.katago_model):
            size = os.path.getsize(self.katago_model) / 1024 / 1024
            print(f"✅ Katago: {size:.1f} MB")
        else:
            print("⚠️ Katago模型未找到")
    
    def detect(self, image_path):
        """检测棋子"""
        results = self.model(image_path, conf=0.15, iou=0.7)[0]
        
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            detections.append({'class': cls, 'conf': conf, 'center': [cx, cy]})
        
        return detections
    
    def nms_merge(self, detections, iou_threshold=0.3):
        """NMS去重"""
        if not detections:
            return []
        
        detections = sorted(detections, key=lambda x: x['conf'], reverse=True)
        keep = []
        
        while detections:
            best = detections.pop(0)
            keep.append(best)
            
            remaining = []
            for d in detections:
                # 简化IoU：距离判断
                dx = best['center'][0] - d['center'][0]
                dy = best['center'][1] - d['center'][1]
                dist = (dx*dx + dy*dy) ** 0.5
                if dist > 25:  # 大于约1.5个格子
                    remaining.append(d)
            detections = remaining
        
        return keep
    
    def estimate_grid(self, stones):
        """估算棋盘网格"""
        xs = [s['center'][0] for s in stones]
        ys = [s['center'][1] for s in stones]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        board_size = max(max_x - min_x, max_y - min_y)
        cell_size = board_size / 18
        margin = cell_size * 0.5
        
        return {
            'min_x': min_x - margin,
            'max_x': max_x + margin,
            'min_y': min_y - margin,
            'max_y': max_y + margin,
            'cell': cell_size
        }
    
    def map_to_grid(self, stones, grid):
        """映射到网格"""
        result = defaultdict(list)
        g = grid
        
        for stone in stones:
            cx, cy = stone['center']
            
            if not (g['min_x'] < cx < g['max_x'] and g['min_y'] < cy < g['max_y']):
                continue
            
            col = int((cx - g['min_x']) / g['cell'])
            row = 18 - int((cy - g['min_y']) / g['cell'])
            
            if 0 <= row <= 18 and 0 <= col <= 18:
                color = 'b' if stone['class'] == 0 else 'w'
                result[(row, col)].append((color, stone['conf']))
        
        # 去重 + 投票
        final = {}
        for pos, stones in result.items():
            if len(stones) == 1:
                final[pos] = stones[0]
            else:
                black = sum(1 for c, _ in stones if c == 'b')
                white = len(stones) - black
                color = 'b' if black > white else 'w'
                conf = max(s[1] for s in stones)
                final[pos] = (color, conf)
        
        return final
    
    def generate_sgf(self, grid_map):
        """生成SGF"""
        sgf = """(;FF[4]CA[UTF-8]SZ[19]
KM[6.5]
PB[Black]
PW[White]
DT[2026-02-06]
RE[Unknown]
"""
        
        sorted_pos = sorted(grid_map.keys(), key=lambda x: (x[0], x[1]))
        
        for row, col in sorted_pos:
            color, conf = grid_map[(row, col)]
            sgf_col = chr(ord('a') + col)
            sgf_row = chr(ord('a') + row)
            letter = 'B' if color == 'b' else 'W'
            sgf += f"{letter}[{sgf_col}{sgf_row}]\n"
        
        sgf += ")"
        return sgf
    
    def analyze_katago(self, sgf_path):
        """Katago分析"""
        if not os.path.exists(self.katago_model):
            return None
        
        print("🔮 Katago分析中...")
        
        # 生成SGF内容
        with open(sgf_path) as f:
            sgf_content = f.read()
        
        # GTP分析
        cmd = f"loadsgf {sgf_path}\ngenmove b\nquit\n"
        
        result = subprocess.run(
            [self.katago_bin, "gtp", "-model", self.katago_model, "-config", self.katago_config],
            input=cmd, capture_output=True, text=True, timeout=60
        )
        
        output = result.stderr + result.stdout
        
        # 提取推荐
        recommendations = []
        for line in output.split('\n'):
            if '=' in line and not line.startswith('?'):
                parts = line.split('=')
                if len(parts) >= 2:
                    move = parts[1].strip()
                    if move and len(move) <= 3:
                        recommendations.append(move)
        
        # 尝试获取胜率信息
        score_info = None
        for line in output.split('\n'):
            if 'score' in line.lower() or 'lead' in line.lower():
                score_info = line.strip()
        
        return {
            "recommendations": recommendations[:5],
            "score_info": score_info,
            "raw": output[:500]
        }
    
    def generate_report(self, stats, katago_info):
        """生成复盘报告"""
        lines = [
            "📊 **围棋AI复盘报告**",
            "",
            "**检测结果:**",
            f"⚫ 黑子: {stats['black']}",
            f"⚪ 白子: {stats['white']}",
            f"📍 总手数: {stats['total']}",
            "",
        ]
        
        if katago_info and katago_info.get('recommendations'):
            lines.append("**Katago推荐 (AI分析):**")
            for i, move in enumerate(katago_info['recommendations'][:5]):
                lines.append(f"  {i+1}. {move}")
        
        if katago_info and katago_info.get('score_info'):
            lines.append(f"\n**分析:** {katago_info['score_info']}")
        
        return '\n'.join(lines)
    
    def process(self, image_path):
        """完整处理流程"""
        print("\n" + "=" * 50)
        print("🎯 围棋AI复盘系统")
        print("=" * 50)
        
        # Step 1: 检测
        print(f"\n📷 检测: {image_path}")
        detections = self.detect(image_path)
        print(f"   原始: {len(detections)} 个")
        
        # Step 2: 去重
        stones = [d for d in detections if d['class'] in [0, 1]]
        stones = self.nms_merge(stones)
        print(f"   去重: {len(stones)} 个")
        
        # Step 3: 统计
        black = sum(1 for s in stones if s['class'] == 0)
        white = sum(1 for s in stones if s['class'] == 1)
        print(f"   黑: {black}, 白: {white}")
        
        # Step 4: 映射
        grid = self.estimate_grid(stones)
        grid_map = self.map_to_grid(stones, grid)
        print(f"   网格: {len(grid_map)} 个位置")
        
        # Step 5: SGF
        sgf_path = image_path.replace('.jpg', '.sgf')
        sgf_content = self.generate_sgf(grid_map)
        with open(sgf_path, 'w') as f:
            f.write(sgf_content)
        print(f"   ✅ SGF: {sgf_path}")
        
        # Step 6: Katago分析
        katago_info = self.analyze_katago(sgf_path)
        
        # Step 7: 报告
        stats = {
            'black': sum(1 for p in grid_map if grid_map[p][0] == 'b'),
            'white': sum(1 for p in grid_map if grid_map[p][0] == 'w'),
            'total': len(grid_map)
        }
        
        print("\n" + "-" * 40)
        print(self.generate_report(stats, katago_info))
        print("-" * 40)
        
        return {
            'sgf_path': sgf_path,
            'stats': stats,
            'katago': katago_info
        }


if __name__ == "__main__":
    app = GoReviewSystem()
    
    if len(sys.argv) > 1:
        app.process(sys.argv[1])
    else:
        test = "/Users/haoc/.openclaw/workspace/merged_dataset/valid/images/0b24b67a3b0a4db1afe841a1acdb1867_jpg.rf.6919d0af4668f6af5b2b0ddd53832e0a.jpg"
        if os.path.exists(test):
            app.process(test)
        else:
            print("用法: python3 go_review_v2.py <图片路径>")
