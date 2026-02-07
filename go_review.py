#!/usr/bin/env python3
"""
围棋AI复盘系统 - 主入口
功能：
1. 图片 → SGF (YOLO检测)
2. 规则分析 (气、眼、选点)
3. LLM复盘指导
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detect import GoBoardDetector
from analyze import GoAnalyzer, parse_sgf


class GoReviewApp:
    """围棋复盘应用"""
    
    def __init__(self):
        self.detector = None
        self.analyzer = None
    
    def load_models(self):
        """加载模型"""
        print("🔧 加载模型...")
        
        model_path = "/Users/haoc/.openclaw/workspace/runs/detect/runs/go_board_yolo26/exp/weights/best.pt"
        if os.path.exists(model_path):
            self.detector = GoBoardDetector(model_path)
        else:
            print(f"❌ 模型未找到: {model_path}")
            return False
        
        self.analyzer = GoAnalyzer()
        print("✅ 模型加载完成\n")
        return True
    
    def image_to_sgf(self, image_path):
        """图片转SGF"""
        if self.detector is None:
            self.load_models()
        
        print(f"📷 处理图片: {image_path}")
        sgf_content, stats = self.detector.process_image(image_path)
        
        sgf_path = Path(image_path).with_suffix(".sgf")
        with open(sgf_path, 'w') as f:
            f.write(sgf_content)
        
        print(f"✅ SGF已保存: {sgf_path}")
        return str(sgf_path), stats
    
    def analyze_sgf(self, sgf_path):
        """分析SGF"""
        print(f"\n📊 分析棋谱: {sgf_path}")
        
        # 读取SGF
        with open(sgf_path) as f:
            sgf_content = f.read()
        
        # 解析并分析
        moves = parse_sgf(sgf_content)
        self.analyzer.apply_moves(moves)
        analysis = self.analyzer.analyze()
        
        # 生成报告
        report = self.analyzer.generate_report(analysis)
        print(report)
        
        return {
            'sgf_content': sgf_content,
            'analysis': analysis,
            'report': report
        }
    
    def full_review(self, image_path):
        """完整复盘流程"""
        print("=" * 60)
        print("🎯 围棋AI复盘系统")
        print("=" * 60)
        
        # Step 1: 图片转SGF
        sgf_path, stats = self.image_to_sgf(image_path)
        
        # Step 2: 分析SGF
        result = self.analyze_sgf(sgf_path)
        
        # Step 3: 生成LLM复盘prompt
        self.generate_llm_prompt(result)
        
        print("\n" + "=" * 60)
        print("✅ 复盘完成!")
        print("=" * 60)
        
        return result
    
    def generate_llm_prompt(self, result):
        """生成LLM复盘prompt"""
        print("\n📝 准备LLM复盘...")
        
        prompt = f"""请对以下围棋对局进行详细复盘分析：

## 棋谱信息
- 总手数: {len(parse_sgf(result['sgf_content']))}
- 黑子数: {result['analysis']['black_count']}
- 白子数: {result['analysis']['white_count']}

## 当前局面分析
{result['report']}

## 建议的下一手
{json.dumps(result['analysis']['suggestions'][:5], indent=2)}

请提供以下复盘内容:
1. **形势判断** - 目前谁领先，领先多少目？
2. **问题手分析** - 指出AI认为的问题手和更好的选点
3. **战略建议** - 下一阶段双方应该注意什么？
4. **具体推荐** - 推荐一手棋的位置和理由
5. **整体评价** - 这盘棋的质量和棋手的特点

请用通俗易懂的语言，帮助棋手提高棋力。"""

        # 保存prompt
        prompt_path = "/Users/haoc/.openclaw/workspace/llm_review_prompt.txt"
        with open(prompt_path, 'w') as f:
            f.write(prompt)
        
        print(f"✅ Prompt已保存: {prompt_path}")
        print("\n" + "-" * 40)
        print("📤 发送给LLM的复盘请求：")
        print("-" * 40)
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)


if __name__ == "__main__":
    app = GoReviewApp()
    
    if len(sys.argv) > 1:
        # 处理指定图片
        result = app.full_review(sys.argv[1])
    else:
        # 默认测试
        test_images = [
            "/Users/haoc/.openclaw/workspace/merged_dataset/valid/images/0b24b67a3b0a4db1afe841a1acdb1867_jpg.rf.6919d0af4668f6af5b2b0ddd53832e0a.jpg",
        ]
        
        if os.path.exists(test_images[0]):
            result = app.full_review(test_images[0])
        else:
            print("❌ 未找到测试图片")
            print("用法: python go_review.py <图片路径>")
