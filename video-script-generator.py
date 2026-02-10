#!/usr/bin/env python3
"""
热点新闻 → 15秒短视频脚本生成器
从每日简报中提取最热话题，生成抖音/快手风格的短视频脚本
"""

import json
import re
from datetime import datetime
from typing import List, Dict

class VideoScriptGenerator:
    def __init__(self):
        self.script_templates = {
            "AI突破": {
                "hook": [
                    "🚨 AI圈又炸了！",
                    "💥 重磅！AI新突破来了",
                    "⚡ 刚刚，AI领域发生大事"
                ],
                "style": "科技感、快节奏"
            },
            "科技公司": {
                "hook": [
                    "🔥 科技圈大瓜！",
                    "💼 大厂又搞事情了",
                    "📢 科技公司最新动态"
                ],
                "style": "八卦感、爆料"
            },
            "政策经济": {
                "hook": [
                    "💰 这个政策影响你的钱包！",
                    "📊 重要！经济新动向",
                    "⚠️ 注意！政策有变化"
                ],
                "style": "严肃、实用"
            },
            "加密货币": {
                "hook": [
                    "🪙 币圈又疯了！",
                    "💸 加密货币最新消息",
                    "🚀 这个币要起飞？"
                ],
                "style": "刺激、投机"
            }
        }
    
    def extract_top_stories(self, briefing_path: str) -> List[Dict]:
        """从简报中提取最热话题"""
        with open(briefing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stories = []
        current_category = None
        current_story = {}
        
        lines = content.split('\n')
        for line in lines:
            # 识别类别
            if line.startswith('## '):
                if '🤖' in line:
                    current_category = "AI突破"
                elif '🏢' in line:
                    current_category = "科技公司"
                elif '📊' in line:
                    current_category = "政策经济"
                elif '💰' in line:
                    current_category = "加密货币"
            
            # 识别故事标题
            if line.startswith('### ') and current_category:
                if current_story:
                    stories.append(current_story)
                
                # 提取标题
                title_match = re.search(r'### \d+\. [📡🐦] (.+)', line)
                if title_match:
                    current_story = {
                        'category': current_category,
                        'title': title_match.group(1).strip(),
                        'content': '',
                        'url': '',
                        'relevance': 0
                    }
            
            # 提取内容
            elif current_story and line.strip() and not line.startswith('#'):
                if line.startswith('🔗'):
                    current_story['url'] = line.replace('🔗', '').strip()
                elif line.startswith('📊 相关性:'):
                    rel_match = re.search(r'(\d+\.?\d*)', line)
                    if rel_match:
                        current_story['relevance'] = float(rel_match.group(1))
                elif not line.startswith('---') and not current_story['content']:
                    current_story['content'] = line.strip()
        
        if current_story:
            stories.append(current_story)
        
        # 按相关性排序，取top 5
        stories.sort(key=lambda x: x['relevance'], reverse=True)
        return stories[:5]
    
    def generate_script(self, story: Dict) -> Dict:
        """生成15秒短视频脚本"""
        category = story['category']
        template = self.script_templates.get(category, self.script_templates["AI突破"])
        
        # 选择hook
        import random
        hook = random.choice(template['hook'])
        
        # 提取关键信息（限制字数）
        title = story['title'][:30]  # 标题限制30字
        content = story['content'][:60]  # 内容限制60字
        
        # 生成脚本
        script = {
            "标题": f"{hook} {title}",
            "时长": "15秒",
            "风格": template['style'],
            "脚本": self._format_script(hook, title, content, category),
            "视觉建议": self._visual_suggestions(category),
            "BGM建议": self._bgm_suggestions(category),
            "字幕": self._subtitle_timing(hook, title, content),
            "原始链接": story['url']
        }
        
        return script
    
    def _format_script(self, hook: str, title: str, content: str, category: str) -> str:
        """格式化脚本文本"""
        script = f"""
【0-2秒】开场
{hook}

【3-8秒】核心内容
{title}
{content}

【9-12秒】解读/影响
"""
        
        if category == "AI突破":
            script += "这意味着AI能力又上了一个台阶！"
        elif category == "科技公司":
            script += "这波操作你怎么看？"
        elif category == "政策经济":
            script += "这对我们有什么影响？"
        elif category == "加密货币":
            script += "你觉得会涨还是跌？"
        
        script += """

【13-15秒】结尾
关注我，每天带你看科技热点！
"""
        return script.strip()
    
    def _visual_suggestions(self, category: str) -> List[str]:
        """视觉建议"""
        visuals = {
            "AI突破": [
                "科技感背景（蓝色/紫色渐变）",
                "代码雨特效",
                "机器人/AI芯片动画",
                "数据流动效果"
            ],
            "科技公司": [
                "公司logo展示",
                "办公室场景",
                "产品界面截图",
                "新闻标题滚动"
            ],
            "政策经济": [
                "图表动画（柱状图/折线图）",
                "货币符号",
                "地图标注",
                "新闻播报风格"
            ],
            "加密货币": [
                "K线图动画",
                "币种logo",
                "金色/绿色背景",
                "数字跳动效果"
            ]
        }
        return visuals.get(category, visuals["AI突破"])
    
    def _bgm_suggestions(self, category: str) -> str:
        """BGM建议"""
        bgm = {
            "AI突破": "电子音乐、科技感强、节奏快",
            "科技公司": "流行音乐、轻快、有节奏感",
            "政策经济": "新闻配乐、严肃、稳重",
            "加密货币": "电音、刺激、紧张感"
        }
        return bgm.get(category, "电子音乐")
    
    def _subtitle_timing(self, hook: str, title: str, content: str) -> List[Dict]:
        """字幕时间轴"""
        return [
            {"时间": "0-2秒", "文字": hook, "大小": "大", "颜色": "黄色"},
            {"时间": "3-5秒", "文字": title[:15], "大小": "中", "颜色": "白色"},
            {"时间": "6-8秒", "文字": title[15:30] if len(title) > 15 else "", "大小": "中", "颜色": "白色"},
            {"时间": "9-12秒", "文字": content[:20], "大小": "小", "颜色": "白色"},
            {"时间": "13-15秒", "文字": "关注我！", "大小": "大", "颜色": "红色"}
        ]
    
    def generate_batch_scripts(self, briefing_path: str, output_path: str):
        """批量生成脚本"""
        print("📝 开始生成短视频脚本...")
        
        # 提取热点故事
        stories = self.extract_top_stories(briefing_path)
        print(f"✓ 提取到 {len(stories)} 个热点话题")
        
        # 生成脚本
        scripts = []
        for i, story in enumerate(stories, 1):
            print(f"\n🎬 生成脚本 {i}/{len(stories)}: {story['title'][:20]}...")
            script = self.generate_script(story)
            scripts.append(script)
        
        # 保存为Markdown
        self._save_as_markdown(scripts, output_path)
        
        # 保存为JSON（方便程序读取）
        json_path = output_path.replace('.md', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 脚本已生成:")
        print(f"   Markdown: {output_path}")
        print(f"   JSON: {json_path}")
    
    def _save_as_markdown(self, scripts: List[Dict], output_path: str):
        """保存为Markdown格式"""
        now = datetime.now()
        md = f"# 🎬 短视频脚本 {now.strftime('%Y-%m-%d')}\n\n"
        md += f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M')} GMT+8\n"
        md += f"> 脚本数量：{len(scripts)} 个\n\n"
        md += "---\n\n"
        
        for i, script in enumerate(scripts, 1):
            md += f"## 脚本 {i}: {script['标题']}\n\n"
            md += f"**时长**: {script['时长']} | **风格**: {script['风格']}\n\n"
            
            md += "### 📜 脚本内容\n\n"
            md += "```\n"
            md += script['脚本']
            md += "\n```\n\n"
            
            md += "### 🎨 视觉建议\n\n"
            for visual in script['视觉建议']:
                md += f"- {visual}\n"
            md += "\n"
            
            md += f"### 🎵 BGM建议\n\n{script['BGM建议']}\n\n"
            
            md += "### 📝 字幕时间轴\n\n"
            md += "| 时间 | 文字 | 大小 | 颜色 |\n"
            md += "|------|------|------|------|\n"
            for sub in script['字幕']:
                if sub['文字']:
                    md += f"| {sub['时间']} | {sub['文字']} | {sub['大小']} | {sub['颜色']} |\n"
            md += "\n"
            
            md += f"### 🔗 原始来源\n\n{script['原始链接']}\n\n"
            md += "---\n\n"
        
        md += "## 💡 使用建议\n\n"
        md += "1. **AI视频生成工具推荐**:\n"
        md += "   - Runway Gen-3\n"
        md += "   - Pika Labs\n"
        md += "   - 剪映AI\n"
        md += "   - 度加AI\n\n"
        md += "2. **发布平台**:\n"
        md += "   - 抖音（推荐）\n"
        md += "   - 快手\n"
        md += "   - 视频号\n"
        md += "   - B站\n\n"
        md += "3. **最佳发布时间**:\n"
        md += "   - 早上 7-9点（上班路上）\n"
        md += "   - 中午 12-14点（午休）\n"
        md += "   - 晚上 19-22点（黄金时段）\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)


def main():
    print("🚀 启动短视频脚本生成器...")
    
    generator = VideoScriptGenerator()
    
    # 使用最新的增强版简报
    now = datetime.now()
    briefing_path = f"/Users/haoc/.openclaw/workspace/briefing-{now.strftime('%Y-%m-%d')}-enhanced.md"
    output_path = f"/Users/haoc/.openclaw/workspace/video-scripts-{now.strftime('%Y-%m-%d')}.md"
    
    try:
        generator.generate_batch_scripts(briefing_path, output_path)
    except FileNotFoundError:
        print(f"❌ 找不到简报文件: {briefing_path}")
        print("💡 请先运行: python3 enhanced-news-aggregator.py")
        return
    
    print("\n🎉 完成！现在可以用这些脚本生成视频了")


if __name__ == "__main__":
    main()
