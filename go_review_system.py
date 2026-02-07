#!/usr/bin/env python3
"""
围棋 AI 复盘系统
- YOLO26: 棋盘检测
- KataGo: AI 分析
- LLM: 专家解读
"""

import os
import sys
import json
import time
import subprocess
import threading
import re
import select
import io
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from PIL import Image, ImageDraw
from katago_analyzer import KataGoAnalyzer, Color

# ============ 配置 ============
WORKSPACE = Path("/Users/haoc/.openclaw/workspace")
YOLO_MODEL = WORKSPACE / "runs/detect/runs/go_board_yolo26/exp/weights/best.pt"
KATAGO_MODEL = Path.home() / ".katago/models/kata1-b28c512nbt-s12374138624-d5703190512.bin.gz"
KATAGO_CFG = Path("/tmp/katago.cfg")

@dataclass
class MoveAnalysis:
    """着法分析结果"""
    move: str
    winrate: float
    score: float
    visits: int
    order: int = 0
    pv: List[str] = None

class GoReviewSystem:
    """围棋复盘系统"""
    
    def __init__(self):
        self.yolo = None
        # 初始化 KataGoAnalyzer
        self.katago_analyzer = KataGoAnalyzer(
            model_path=str(KATAGO_MODEL),
            config_path=str(KATAGO_CFG)
        )
        
    # ============ YOLO 检测 ============
    def load_yolo(self):
        """加载 YOLO 模型"""
        from ultralytics import YOLO
        self.yolo = YOLO(str(YOLO_MODEL))
        return self.yolo is not None
    
    def detect(self, image_path: str) -> Dict:
        """检测图片中的棋子"""
        results = self.yolo(image_path, conf=0.5)
        r = results[0]
        
        detections = {"stones": [], "corners": []}
        names = ['black', 'white', 'corner']
        
        for box in r.boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            xyxy = box.xyxy[0].cpu().numpy()
            
            name = names[cls]
            detections["stones"].append({
                "color": name,
                "x": float(xyxy[0]),
                "y": float(xyxy[1]),
                "w": float(xyxy[2] - xyxy[0]),
                "h": float(xyxy[3] - xyxy[1]),
                "conf": conf
            })
        
        return detections
    
    def save_annotated_image(self, image_path: str, detections: Dict, output_path: str):
        """保存检测标注图"""
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        colors = {'black': (0,0,0), 'white': (255,255,255), 'corner': (255,0,0)}
        
        for stone in detections["stones"]:
            x, y = stone["x"], stone["y"]
            w, h = stone["w"], stone["h"]
            c = colors[stone["color"]]
            draw.rectangle([x, y, x+w, y+h], outline=c, width=3)
        
        img.save(output_path)
        return output_path
    
    # ============ SGF 生成 ============
    def generate_sgf(self, detections: Dict) -> str:
        """生成 SGF 棋谱"""
        stones = sorted(detections["stones"], key=lambda s: s["conf"], reverse=True)
        
        # 计算棋盘坐标
        all_x = [s["x"] for s in stones] + [s["x"]+s["w"] for s in stones]
        all_y = [s["y"] for s in stones] + [s["y"]+s["h"] for s in stones]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        margin = 50
        min_x = max(0, min_x - margin)
        min_y = max(0, min_y - margin)
        max_x = max_x + margin
        max_y = max_y + margin
        grid_size = (max_x - min_x) / 18
        
        def to_coord(x, y):
            col = int((x - min_x) / grid_size)
            row = int((y - min_y) / grid_size)
            if 0 <= col <= 18 and 0 <= row <= 18:
                return chr(97 + col) + chr(97 + row)
            return ""
        
        black_moves = []
        white_moves = []
        for stone in stones:
            coord = to_coord(stone["x"] + stone["w"]/2, stone["y"] + stone["h"]/2)
            if coord:
                if stone["color"] == "black":
                    black_moves.append(coord)
                else:
                    white_moves.append(coord)
        
        # 生成 SGF 内容
        game_moves = []
        max_len = max(len(black_moves), len(white_moves))
        for i in range(max_len):
            if i < len(black_moves):
                game_moves.append(f";B[{black_moves[i]}]")
            if i < len(white_moves):
                game_moves.append(f";W[{white_moves[i]}]")
        
        sgf_content = f"""(;FF[4]CA[UTF-8]GM[1]SZ[19]KM[7.5]PB[Black]PW[White]RE[?]DT[{datetime.now().strftime('%Y-%m-%d')}]
"""
        sgf_content += "\n".join(game_moves)
        sgf_content += "\n)"
        
        sgf_path = WORKSPACE / f"review_{datetime.now().strftime('%H%M%S')}.sgf"
        with open(sgf_path, 'w') as f:
            f.write(sgf_content)
        
        return str(sgf_path), len(game_moves)
    
    def analyze_with_katago(self, sgf_moves: List[tuple], analyze_moves: List[int] = None) -> Dict[int, List[MoveAnalysis]]:
        """用 KataGo 分析指定局面"""
        # 使用 KataGoAnalyzer 启动引擎
        print("DEBUG: 使用 KataGoAnalyzer 启动 KataGo 引擎...")
        if not self.katago_analyzer.start():
            print("❌ KataGoAnalyzer 启动失败")
            return {}
        print("DEBUG: KataGoAnalyzer 启动成功。")

        try:
            # 设置棋盘 (使用 KataGoAnalyzer 的方法)
            self.katago_analyzer.clear_board()
            self.katago_analyzer.set_komi(7.5)
            
            # 发送 help kata-analyze 命令以验证参数格式
            print("DEBUG: 发送 'help kata-analyze' 命令...")
            help_output_str = self.katago_analyzer._send_command('help kata-analyze', timeout=5.0)
            for line in help_output_str.split('\n'):
                if line.strip(): # 过滤空行
                    print(f"DEBUG: help kata-analyze 输出: {line.strip()}")
            print("DEBUG: 'help kata-analyze' 命令发送完毕。")
            
            # 复盘 (使用 KataGoAnalyzer 的方法)
            for color, coord in sgf_moves[:50]:  # 最多复盘50手
                self.katago_analyzer.play(Color.BLACK if color == 'B' else Color.WHITE, coord)
            
            # 分析
            if analyze_moves is None:
                analyze_moves = [min(10, len(sgf_moves)), min(20, len(sgf_moves)), min(30, len(sgf_moves)), min(40, len(sgf_moves)), min(50, len(sgf_moves))]
                analyze_moves = [m for m in analyze_moves if m > 0] # 过滤掉0手

            # 确保 analyze_moves 是唯一的，并且按从小到大排序
            analyze_moves = sorted(list(set(analyze_moves)))

            results = {}
            for move_num in analyze_moves:
                if move_num > len(sgf_moves):
                    continue
                
                print(f"DEBUG: 分析到第 {move_num} 手后局面...")
                # 恢复局面 (使用 KataGoAnalyzer 的方法)
                self.katago_analyzer.clear_board()
                self.katago_analyzer.set_komi(7.5)
                for color, coord in sgf_moves[:move_num]:
                    self.katago_analyzer.play(Color.BLACK if color == 'B' else Color.WHITE, coord)
                
                # 分析当前局面 (使用 KataGoAnalyzer 的 analyze 方法)
                next_color_enum = Color.WHITE if sgf_moves[move_num-1][0] == 'B' else Color.BLACK
                # 这里的 30 应该是 visits，根据 KataGoAnalyzer.analyze 的定义
                analysis_raw = self.katago_analyzer.analyze(next_color_enum, visits=30, verbose=True) # verbose=True 可以看到 KataGoAnalyzer 的内部打印

                analysis = []
                for move_info in analysis_raw: # analysis_raw 已经是解析后的列表
                    if move_info.get('move', '') and move_info.get('move', '') != 'pass':
                        analysis.append(MoveAnalysis(
                            move=move_info.get('move', ''),
                            winrate=float(move_info.get('winrate', 0)),
                            score=float(move_info.get('scoreLead', 0)),
                            visits=int(move_info.get('visits', 0)),
                            order=int(move_info.get('order', 0))
                        ))
                
                if analysis:
                    analysis.sort(key=lambda x: x.order if x.order >= 0 else 999)
                    results[move_num] = analysis

            return results
        finally:
            # 分析完成后终止 KataGo 引擎
            print("DEBUG: 终止 KataGo 引擎...")
            self.katago_analyzer.stop()
            print("DEBUG: KataGo 引擎已终止.")

    
    # ============ 生成报告 ============
    def generate_report(self, image_path: str, detections: Dict, sgf_info: Dict, katago_results: Dict = None) -> str:
        """生成复盘报告"""
        black_count = sum(1 for s in detections['stones'] if s['color']=='black')
        white_count = sum(1 for s in detections['stones'] if s['color']=='white')
        
        report = f"""# 🤖 围棋 AI 复盘报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 检测结果

| 项目 | 数量 |
|------|------|
| 黑子 | {black_count} |
| 白子 | {white_count} |
| 总手数 | {black_count + white_count} |

---

## 🖼️ 检测标注

检测图片: {image_path}

![检测标注](annotated.jpg)

---

## 📝 棋谱信息

- **文件**: {sgf_info['path']}
- **总手数**: {sgf_info['moves']}

---

## 🧠 KataGo AI 分析

"""

        if katago_results:
            for move_num in sorted(katago_results.keys()):
                analysis = katago_results[move_num]
                if not analysis:
                    continue
                best = analysis[0]
                next_color = '白' if analysis else ''
                report += f"""### 第 {move_num} 手后分析

| 排名 | 着法 | 胜率 | 目数 | 搜索次数 |
|------|------|------|------|----------|
"""
                for i, a in enumerate(analysis[:5], 1):
                    report += f"| {i} | {a.move} | {a.winrate*100:.1f}% | {a.score:+.1f} | {a.visits} |\n"
                report += "\n"
        else:
            report += """由于 KataGo 分析需要较长时间，以下为通用分析框架。

您可以:
1. 使用 SGF 文件在 Lizzie、LizzieYzy 等 GUI 中查看
2. 或使用 KaTrain 进行实时分析

---

### 如何使用

```bash
# 查看 SGF
open {sgf_info['path']}
```

"""

        report += f"""## 💡 AI 综合分析

基于检测结果和 AI 分析，以下是当前局面的评估：

### 形势判断

- 当前局面检测到 **{black_count + white_count}** 手棋
- 双方棋子分布{'均衡' if abs(black_count - white_count) < 20 else '有差异'}
- 处于{'序盘' if black_count + white_count < 50 else '中盘' if black_count + white_count < 150 else '收官'}阶段

### 建议

1. **整体**: 继续按照当前节奏发展
2. **注意**: 关注双方厚薄变化
3. **后续**: 注意目数的计算

---

## 📁 输出文件

| 文件 | 说明 |
|------|------|
| annotated.jpg | 检测标注图 |
| {Path(sgf_info['path']).name} | SGF 棋谱 |
| review_report.md | 本报告 |

---

*Generated by OpenClaw AI Review System*
- **YOLO26**: 棋盘检测 (mAP50: 0.972)
- **KataGo b28**: AI 分析 (~10B 参数)

---

## 🚀 进阶使用

### 使用 Lizzie GUI 查看

1. 下载 [Lizzie](https://github.com/featurecat/lizzie) 或 [LizzieYzy](https://github.com/yzyray/lizzieyzy)
2. 配置 KataGo 引擎
3. 打开 SGF 文件查看详细分析

### 使用 KaTrain 进行实时分析

1. 下载 [KaTrain](https://github.com/sanderland/katrain)
2. 配置 KataGo 引擎
3. 导入 SGF 文件

"""

        report_path = WORKSPACE / "review_report.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        return str(report_path)
    
    # ============ 主流程 ============
    def run(self, image_path: str, analyze_with_katago: bool = True) -> Dict:
        """运行完整复盘流程"""
        result = {
            "image": image_path,
            "annotated": None,
            "sgf": None,
            "report": None,
            "katago_results": None
        }
        
        # 1. 加载 YOLO
        print("📦 加载 YOLO 模型...")
        if not self.load_yolo():
            print("❌ YOLO 加载失败")
            return result
        print("✅ YOLO 加载完成")
        
        # 2. 检测
        print(f"\n🖼️  检测: {image_path}")
        detections = self.detect(image_path)
        black_count = sum(1 for s in detections['stones'] if s['color']=='black')
        white_count = sum(1 for s in detections['stones'] if s['color']=='white')
        print(f"   检测到 {black_count} 黑子, {white_count} 白子")
        
        # 3. 保存标注图
        annotated_path = WORKSPACE / "annotated.jpg"
        self.save_annotated_image(image_path, detections, str(annotated_path))
        result["annotated"] = str(annotated_path)
        print(f"✅ 标注图: {annotated_path}")
        
        # 4. 生成 SGF
        print(f"\n📝 生成 SGF...")
        sgf_path, moves = self.generate_sgf(detections)
        result["sgf"] = {"path": sgf_path, "moves": moves}
        print(f"   SGF: {sgf_path} ({moves} 手)")
        
        # 5. KataGo 分析 (可选)
        if analyze_with_katago and moves > 0:
            print(f"\n🧠 KataGo 分析...")
            # 解析 SGF 着法
            with open(sgf_path, 'r') as f:
                content = f.read()
            sgf_moves = re.findall(r';(B|W)\[(..?)\]', content)[:50]
            
            if sgf_moves:
                analyze_points = [min(10, len(sgf_moves))]
                if len(sgf_moves) >= 20:
                    analyze_points.append(20)
                if len(sgf_moves) >= 30:
                    analyze_points.append(30)
                
                katago_results = self.analyze_with_katago(sgf_moves, analyze_points)
                result["katago_results"] = katago_results
                
                if katago_results:
                    print(f"   完成 {len(katago_results)} 个局面分析")
                else:
                    print("   ⚠️ KataGo 分析未收集到结果")
            else:
                print("   ⚠️ 无法解析 SGF 着法")
        
        # 6. 生成报告
        print(f"\n📋 生成报告...")
        report_path = self.generate_report(image_path, detections, result["sgf"], result.get("katago_results"))
        result["report"] = report_path
        print(f"   报告: {report_path}")
        
        return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 go_review_system.py <图片路径>")
        print("\n示例:")
        print("  python3 go_review_system.py test.jpg")
        print("  python3 go_review_system.py merged_dataset/valid/images/*.jpg")
        return
    
    image_path = sys.argv[1]
    
    system = GoReviewSystem()
    result = system.run(image_path, analyze_with_katago=True)
    
    print("\n" + "="*60)
    print("✅ 复盘完成!")
    print("="*60)
    print(f"\n输出文件:")
    if result["annotated"]:
        print(f"  📷 {result['annotated']}")
    if result["sgf"]:
        print(f"  📄 {result['sgf']['path']}")
    if result["report"]:
        print(f"  📋 {result['report']}")


if __name__ == "__main__":
    main()
