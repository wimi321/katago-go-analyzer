#!/usr/bin/env python3
"""
完整围棋复盘流程
1. 图片 → 2. YOLO检测 → 3. 棋谱生成 → 4. KataGo分析 → 5. AI复盘输出
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# 配置路径
WORKSPACE = Path("/Users/haoc/.openclaw/workspace")
MODEL_PATH = WORKSPACE / "runs/detect/runs/go_board_yolo26/exp/weights/best.pt"
KATAGO_MODEL = Path("/Users/haoc/.openclaw/workspace/katago_model.bin.gz")

# 导入模块
from ultralytics import YOLO
from katago_analyzer import KataGoAnalyzer, Color

class GoReviewPipeline:
    """围棋复盘完整流程"""
    
    def __init__(self):
        self.yolo_model = None
        self.katago = None
        self.results = {}
        
    def load_models(self) -> bool:
        """加载模型"""
        print("\n" + "="*60)
        print("📦 加载模型...")
        print("="*60)
        
        # YOLO
        if MODEL_PATH.exists():
            self.yolo_model = YOLO(str(MODEL_PATH))
            print(f"✅ YOLO: {MODEL_PATH.name}")
        else:
            print(f"❌ YOLO 模型不存在: {MODEL_PATH}")
            return False
        
        # KataGo
        if KATAGO_MODEL.exists():
            self.katago = KataGoAnalyzer(str(KATAGO_MODEL))
            if self.katago.start():
                print(f"✅ KataGo: {KATAGO_MODEL.name}")
            else:
                print("❌ KataGo 启动失败")
                return False
        else:
            print(f"❌ KataGo 模型不存在: {KATAGO_MODEL}")
            return False
        
        return True
    
    def detect_from_image(self, image_path: str) -> Dict:
        """从图片检测"""
        print("\n" + "="*60)
        print("🔍 YOLO 检测...")
        print("="*60)
        print(f"图片: {image_path}")
        
        results = self.yolo_model(image_path, conf=0.5, iou=0.5)
        r = results[0]
        
        detections = {
            "stones": [],
            "corners": [],
            "image_size": r.orig_shape
        }
        
        # 解析检测结果
        if r.boxes:
            for box in r.boxes:
                cls = int(box.cls)
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf)
                
                # 类别: 0=black, 1=white, 2=corner
                if cls == 0:
                    detections["stones"].append({
                        "color": "black",
                        "x": float(xyxy[0]),
                        "y": float(xyxy[1]),
                        "w": float(xyxy[2] - xyxy[0]),
                        "h": float(xyxy[3] - xyxy[1]),
                        "conf": conf
                    })
                elif cls == 1:
                    detections["stones"].append({
                        "color": "white",
                        "x": float(xyxy[0]),
                        "y": float(xyxy[1]),
                        "w": float(xyxy[2] - xyxy[0]),
                        "h": float(xyxy[3] - xyxy[1]),
                        "conf": conf
                    })
                elif cls == 2:
                    detections["corners"].append({
                        "x": float(xyxy[0]),
                        "y": float(xyxy[1]),
                        "w": float(xyxy[2] - xyxy[0]),
                        "h": float(xyxy[3] - xyxy[1]),
                        "conf": conf
                    })
        
        print(f"检测到:")
        print(f"  黑子: {sum(1 for s in detections['stones'] if s['color']=='black')}")
        print(f"  白子: {sum(1 for s in detections['stones'] if s['color']=='white')}")
        print(f"  角点: {len(detections['corners'])}")
        
        self.results["detect"] = detections
        return detections
    
    def generate_sgf(self, detections: Dict, sgf_path: str = None) -> str:
        """生成 SGF 棋谱"""
        print("\n" + "="*60)
        print("📝 生成 SGF 棋谱...")
        print("="*60)
        
        stones = sorted(detections["stones"], key=lambda s: s["conf"], reverse=True)
        
        # 根据棋子颜色和置信度排序生成棋谱
        # 简单的策略：黑子在前，白子在后（假设图片顺序）
        
        # 生成 SGF
        if not sgf_path:
            sgf_path = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sgf"
        
        # 估算棋盘范围
        if detections["corners"]:
            corners = detections["corners"]
            min_x = min(c["x"] for c in corners)
            max_x = max(c["x"] + c["w"] for c in corners)
            min_y = min(c["y"] for c in corners)
            max_y = max(c["y"] + c["h"] for c in corners)
        else:
            # 使用所有棋子的边界
            all_x = [s["x"] for s in stones] + [s["x"]+s["w"] for s in stones]
            all_y = [s["y"] for s in stones] + [s["y"]+s["h"] for s in stones]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
        
        # 添加边距
        margin = 50
        min_x = max(0, min_x - margin)
        min_y = max(0, min_y - margin)
        max_x = max_x + margin
        max_y = max_y + margin
        
        # 计算格子大小和棋盘位置
        width = max_x - min_x
        height = max_y - min_y
        
        # 假设 19x19 棋盘
        board_size = 19
        grid_size = width / 18  # 近似格子大小
        
        def to_coord(x, y):
            """像素坐标转 SGF 坐标"""
            col = int((x - min_x) / grid_size)
            row = int((y - min_y) / grid_size)
            # SGF: a-t 是列 (0-18), a-t 是行 (0-18)
            if 0 <= col <= 18 and 0 <= row <= 18:
                return chr(97 + col) + chr(97 + row)
            return ""
        
        # 生成着法序列
        moves = []
        for stone in stones:
            coord = to_coord(stone["x"] + stone["w"]/2, stone["y"] + stone["h"]/2)
            if coord:
                moves.append((stone["color"], coord))
        
        # 按顺序排列（假设置信度高的先下）
        black_moves = [m[1] for m in moves if m[0] == "black"]
        white_moves = [m[1] for m in moves if m[0] == "white"]
        
        # 合并成完整对局
        game_moves = []
        max_len = max(len(black_moves), len(white_moves))
        for i in range(max_len):
            if i < len(black_moves):
                game_moves.append(("B", black_moves[i]))
            if i < len(white_moves):
                game_moves.append(("W", white_moves[i]))
        
        # 生成 SGF 内容
        sgf_content = f"""(;FF[4]CA[UTF-8]GM[1]SZ[19]KM[7.5]PB[Black]PW[White]RE[?]DT[{datetime.now().strftime('%Y-%m-%d')}]
"""
        for i, (color, coord) in enumerate(game_moves, 1):
            sgf_content += f";{color}[{coord}]\n"
        
        sgf_content += ")"
        
        # 保存
        sgf_full_path = WORKSPACE / sgf_path
        with open(sgf_full_path, "w", encoding="utf-8") as f:
            f.write(sgf_content)
        
        print(f"✅ SGF 已生成: {sgf_path}")
        print(f"   着法数: {len(game_moves)}")
        
        self.results["sgf"] = {
            "path": str(sgf_full_path),
            "moves": len(game_moves),
            "black_moves": len(black_moves),
            "white_moves": len(white_moves)
        }
        
        return str(sgf_full_path)
    
    def analyze_with_katago(self, sgf_path: str, analyze_moves: List[int] = None) -> Dict:
        """用 KataGo 分析"""
        print("\n" + "="*60)
        print("🧠 KataGo 分析...")
        print("="*60)
        
        # 设置棋盘
        self.katago.clear_board()
        self.katago.set_komi(7.5)
        
        # 加载 SGF 着法
        with open(sgf_path, "r") as f:
            content = f.read()
        
        # 解析 SGF 提取着法
        import re
        moves = re.findall(r';(B|W)\[(..?)\]', content)
        
        # 复盘
        for color_char, coord in moves:
            color = Color.BLACK if color_char == "B" else Color.WHITE
            self.katago.play(color, coord)
        
        print(f"已加载 {len(moves)} 手棋")
        
        # 分析关键局面
        if analyze_moves is None:
            # 默认分析: 每10手分析一次，加上最后几手
            total = len(moves)
            analyze_moves = [i for i in range(10, min(total, 50), 10)]
            if total > 20:
                analyze_moves.extend([total-2, total-1])
        
        analysis_results = {}
        
        for move_num in analyze_moves:
            if move_num > len(moves):
                continue
            
            print(f"\n分析第 {move_num} 手...")
            
            # 恢复到该局面
            self.katago.clear_board()
            for i, (color_char, coord) in enumerate(moves[:move_num]):
                color = Color.BLACK if color_char == "B" else Color.WHITE
                self.katago.play(color, coord)
            
            # 分析当前局面 (下一手是白棋，因为刚下了黑棋)
            results = self.katago.analyze(Color.WHITE, visits=50)
            
            if results:
                best = results[0]
                analysis_results[move_num] = {
                    "move": best.move,
                    "winrate": best.winrate,
                    "score_lead": best.score_lead,
                    "visits": best.visits,
                    "top_moves": [
                        {
                            "move": r.move,
                            "winrate": r.winrate,
                            "score_lead": r.score_lead
                        }
                        for r in results[:5]
                    ]
                }
                
                print(f"  建议: {best.move} | 胜率: {best.winrate*100:.1f}% | 目数: {best.score_lead:+.1f}")
        
        self.results["analysis"] = analysis_results
        return analysis_results
    
    def generate_review_report(self) -> str:
        """生成复盘报告"""
        print("\n" + "="*60)
        print("📋 生成复盘报告...")
        print("="*60)
        
        report = f"""
# 🤖 围棋 AI 复盘报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 检测结果
- 图片尺寸: {self.results.get('detect', {}).get('image_size', 'N/A')}
- 黑子数: {sum(1 for s in self.results.get('detect', {}).get('stones', []) if s['color']=='black')}
- 白子数: {sum(1 for s in self.results.get('detect', {}).get('stones', []) if s['color']=='white')}
- 角点数: {len(self.results.get('detect', {}).get('corners', []))}

## 📝 棋谱信息
- 文件: {self.results.get('sgf', {}).get('path', 'N/A')}
- 总手数: {self.results.get('sgf', {}).get('moves', 0)}

## 🧠 KataGo 分析

### 关键局面分析
"""
        
        analysis = self.results.get("analysis", {})
        for move_num in sorted(analysis.keys()):
            data = analysis[move_num]
            report += f"""
#### 第 {move_num} 手后
- **AI 建议**: {data['move']}
- **胜率**: {data['winrate']*100:.1f}%
- **目数差**: {data['score_lead']:+.1f}
- **搜索次数**: {data['visits']}

候选着法:
"""
            for i, m in enumerate(data['top_moves'], 1):
                report += f"{i}. {m['move']} (胜率 {m['winrate']*100:.1f}%, 目数 {m['score_lead']:+.1f})\n"
        
        report += """
## 💡 总结

本复盘由以下 AI 组件完成:
1. **YOLO26** - 棋盘和棋子检测
2. **KataGo b28** - AI 围棋分析和着法推荐

---
*Generated by OpenClaw Go Review System*
"""
        
        report_path = WORKSPACE / "review_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"✅ 报告已生成: {report_path}")
        return str(report_path)
    
    def cleanup(self):
        """清理资源"""
        if self.katago:
            self.katago.stop()
        print("\n✅ 资源已清理")
    
    def run(self, image_path: str):
        """运行完整流程"""
        try:
            # 1. 加载模型
            if not self.load_models():
                return None
            
            # 2. 检测
            detections = self.detect_from_image(image_path)
            
            # 3. 生成 SGF
            sgf_path = self.generate_sgf(detections)
            
            # 4. KataGo 分析
            self.analyze_with_katago(sgf_path)
            
            # 5. 生成报告
            report_path = self.generate_review_report()
            
            print("\n" + "="*60)
            print("✅ 复盘完成!")
            print("="*60)
            
            return report_path
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.cleanup()


def demo():
    """演示 - 使用测试图片"""
    pipeline = GoReviewPipeline()
    
    # 找一张测试图片
    test_images = list(WORKSPACE.glob("*.jpg")) + list(WORKSPACE.glob("*.png"))
    if test_images:
        image_path = str(test_images[0])
        print(f"使用测试图片: {image_path}")
        pipeline.run(image_path)
    else:
        print("未找到测试图片，请提供图片路径")
        print("用法: python3 full_pipeline.py <图片路径>")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        demo()
    # pipeline.run(image_path)
