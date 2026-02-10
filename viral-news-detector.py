#!/usr/bin/env python3
"""
热点新闻爆点识别器 - 自动识别高流量潜力的新闻
基于多维度评分系统，筛选出最适合做成短视频的内容
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Tuple

class ViralNewsDetector:
    def __init__(self):
        # 爆点关键词权重
        self.viral_keywords = {
            # 政治军事（高关注度）
            "逮捕": 10, "总统": 9, "战争": 9, "冲突": 8, "制裁": 7,
            "政变": 10, "暗杀": 10, "间谍": 8, "核武器": 9,
            
            # 科技突破（AI圈热点）
            "突破": 8, "发布": 7, "超越": 8, "首次": 7, "革命性": 9,
            "AGI": 10, "量子": 8, "颠覆": 9,
            
            # 商业金融（财富相关）
            "破产": 9, "暴涨": 8, "暴跌": 8, "裁员": 7, "收购": 7,
            "首富": 8, "亿": 6, "十亿": 8, "百亿": 9,
            
            # 争议话题（引发讨论）
            "争议": 7, "丑闻": 9, "泄露": 8, "禁止": 7, "封杀": 8,
            "抗议": 7, "罢工": 7,
            
            # 灾难事故（紧迫感）
            "爆炸": 9, "坠毁": 9, "地震": 8, "火灾": 7, "泄漏": 8,
            
            # 名人效应
            "马斯克": 7, "特朗普": 7, "拜登": 6, "普京": 7,
            "OpenAI": 6, "谷歌": 5, "苹果": 5,
        }
        
        # 情绪词权重
        self.emotion_words = {
            "震惊": 8, "惊人": 7, "疯狂": 8, "恐怖": 7, "史无前例": 9,
            "炸了": 8, "爆了": 8, "火了": 7, "疯了": 8,
            "重磅": 7, "紧急": 8, "突发": 9, "刚刚": 7,
        }
        
        # 负面指标（降低分数）
        self.spam_indicators = [
            "免费信号", "加入群", "telegram", "准确率", "盈利",
            "点击链接", "关注领取", "限时优惠"
        ]
    
    def calculate_viral_score(self, story: Dict) -> Tuple[float, List[str]]:
        """计算新闻的爆点分数"""
        text = (story.get('title', '') + ' ' + story.get('content', '')).lower()
        score = 0.0
        reasons = []
        
        # 1. 关键词匹配
        for keyword, weight in self.viral_keywords.items():
            if keyword.lower() in text:
                score += weight
                reasons.append(f"关键词:{keyword}(+{weight})")
        
        # 2. 情绪词匹配
        for emotion, weight in self.emotion_words.items():
            if emotion in text:
                score += weight
                reasons.append(f"情绪词:{emotion}(+{weight})")
        
        # 3. 数字冲击力（大数字更吸引眼球）
        numbers = re.findall(r'\d+(?:亿|万|千万|百万)', text)
        if numbers:
            score += len(numbers) * 5
            reasons.append(f"大数字:{','.join(numbers[:2])}(+{len(numbers)*5})")
        
        # 4. 时效性（"刚刚"、"今天"、"突发"）
        time_words = ["刚刚", "今天", "突发", "最新", "just", "breaking"]
        for word in time_words:
            if word in text:
                score += 6
                reasons.append(f"时效性:{word}(+6)")
                break
        
        # 5. 冲突性（对立、矛盾）
        conflict_words = ["vs", "对抗", "反对", "批评", "指责", "vs."]
        for word in conflict_words:
            if word in text:
                score += 5
                reasons.append(f"冲突性:{word}(+5)")
                break
        
        # 6. 反转性（"竟然"、"没想到"）
        twist_words = ["竟然", "没想到", "意外", "反转", "惊人"]
        for word in twist_words:
            if word in text:
                score += 4
                reasons.append(f"反转性:{word}(+4)")
                break
        
        # 7. 负面指标（spam检测）
        spam_count = sum(1 for indicator in self.spam_indicators if indicator in text)
        if spam_count > 0:
            penalty = spam_count * 20
            score -= penalty
            reasons.append(f"spam惩罚:(-{penalty})")
        
        # 8. 来源权威性加分
        if story.get('source') == 'tavily':
            score += 10
            reasons.append("权威来源:Tavily(+10)")
        
        # 9. 相关性加分
        relevance = story.get('relevance_score', 0)
        if relevance > 0.8:
            score += 5
            reasons.append(f"高相关性(+5)")
        
        return score, reasons
    
    def generate_viral_script(self, story: Dict, score: float, reasons: List[str]) -> Dict:
        """为高分新闻生成爆款脚本"""
        title = story.get('title', '')[:30]
        content = story.get('content', '')[:100]
        category = story.get('category', 'AI突破')
        
        # 根据内容类型选择hook
        hooks = self._select_hook(content, category)
        
        # 生成脚本
        script = {
            "爆点分数": round(score, 1),
            "爆点原因": reasons[:3],  # 只显示前3个主要原因
            "标题": f"{hooks['emoji']} {hooks['hook']} {title}",
            "时长": "15秒",
            "风格": hooks['style'],
            "脚本": self._format_viral_script(hooks, title, content),
            "视觉建议": self._viral_visual_suggestions(content),
            "BGM建议": hooks['bgm'],
            "字幕": self._viral_subtitle_timing(hooks, title, content),
            "原始链接": story.get('url', ''),
            "预估流量": self._estimate_traffic(score)
        }
        
        return script
    
    def _select_hook(self, content: str, category: str) -> Dict:
        """根据内容选择最佳hook"""
        content_lower = content.lower()
        
        # 政治军事类
        if any(word in content_lower for word in ["逮捕", "总统", "战争", "政变"]):
            return {
                "emoji": "🚨",
                "hook": "重大突发！",
                "style": "紧张、新闻感",
                "bgm": "紧张的新闻配乐"
            }
        
        # 科技突破类
        if any(word in content_lower for word in ["突破", "发布", "超越", "agi"]):
            return {
                "emoji": "💥",
                "hook": "科技圈炸了！",
                "style": "科技感、震撼",
                "bgm": "电子音乐、节奏强"
            }
        
        # 商业金融类
        if any(word in content_lower for word in ["破产", "暴涨", "暴跌", "亿"]):
            return {
                "emoji": "💰",
                "hook": "这个数字太疯狂！",
                "style": "刺激、财富感",
                "bgm": "紧张刺激的音乐"
            }
        
        # 争议丑闻类
        if any(word in content_lower for word in ["争议", "丑闻", "泄露", "禁止"]):
            return {
                "emoji": "🔥",
                "hook": "大瓜来了！",
                "style": "八卦、爆料",
                "bgm": "悬疑、八卦风格"
            }
        
        # 默认
        return {
            "emoji": "⚡",
            "hook": "刚刚发生！",
            "style": "快节奏、紧迫",
            "bgm": "快节奏电子乐"
        }
    
    def _format_viral_script(self, hooks: Dict, title: str, content: str) -> str:
        """格式化爆款脚本"""
        return f"""
【0-2秒】强力开场
{hooks['emoji']} {hooks['hook']}

【3-8秒】核心爆点
{title}
{content[:50]}

【9-12秒】冲击解读
这件事影响有多大？
（展示关键数据/画面）

【13-15秒】强力CTA
关注我，第一时间看热点！
""".strip()
    
    def _viral_visual_suggestions(self, content: str) -> List[str]:
        """爆款视觉建议"""
        suggestions = [
            "震撼开场（闪光/爆炸效果）",
            "关键信息放大特写",
            "快速剪辑（0.5秒一个镜头）",
            "红色/黄色警示色调"
        ]
        
        # 根据内容添加特定建议
        if "逮捕" in content or "总统" in content:
            suggestions.append("新闻画面 + 警报特效")
        if "亿" in content or "暴涨" in content:
            suggestions.append("数字跳动动画")
        if "AI" in content or "突破" in content:
            suggestions.append("科技感粒子特效")
        
        return suggestions
    
    def _viral_subtitle_timing(self, hooks: Dict, title: str, content: str) -> List[Dict]:
        """爆款字幕时间轴"""
        return [
            {"时间": "0-2秒", "文字": f"{hooks['emoji']} {hooks['hook']}", "大小": "特大", "颜色": "红色", "特效": "闪烁"},
            {"时间": "3-5秒", "文字": title[:15], "大小": "大", "颜色": "黄色", "特效": "放大"},
            {"时间": "6-8秒", "文字": content[:20], "大小": "中", "颜色": "白色", "特效": "无"},
            {"时间": "9-12秒", "文字": "影响有多大？", "大小": "大", "颜色": "红色", "特效": "震动"},
            {"时间": "13-15秒", "文字": "关注我！", "大小": "特大", "颜色": "红色", "特效": "闪烁"}
        ]
    
    def _estimate_traffic(self, score: float) -> str:
        """预估流量潜力"""
        if score >= 50:
            return "🔥🔥🔥 爆款潜力（预估10万+播放）"
        elif score >= 30:
            return "🔥🔥 高流量潜力（预估5万+播放）"
        elif score >= 20:
            return "🔥 中等流量（预估1万+播放）"
        else:
            return "普通流量（预估5000+播放）"
    
    def analyze_briefing(self, briefing_path: str) -> List[Dict]:
        """分析简报，识别爆点新闻"""
        print("🔍 开始分析新闻爆点...")
        
        # 读取简报
        with open(briefing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有新闻
        stories = self._extract_stories(content)
        print(f"✓ 提取到 {len(stories)} 条新闻")
        
        # 计算爆点分数
        scored_stories = []
        for story in stories:
            score, reasons = self.calculate_viral_score(story)
            if score > 0:  # 只保留正分
                story['viral_score'] = score
                story['viral_reasons'] = reasons
                scored_stories.append(story)
        
        # 按分数排序
        scored_stories.sort(key=lambda x: x['viral_score'], reverse=True)
        
        print(f"✓ 识别到 {len(scored_stories)} 条有效新闻")
        print(f"🔥 最高分: {scored_stories[0]['viral_score']:.1f}" if scored_stories else "")
        
        return scored_stories
    
    def _extract_stories(self, content: str) -> List[Dict]:
        """从简报中提取新闻"""
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
            
            # 识别故事
            if line.startswith('### ') and current_category:
                if current_story:
                    stories.append(current_story)
                
                title_match = re.search(r'### \d+\. [📡🐦] (.+)', line)
                if title_match:
                    current_story = {
                        'category': current_category,
                        'title': title_match.group(1).strip(),
                        'content': '',
                        'url': '',
                        'relevance_score': 0,
                        'source': ''
                    }
            
            # 提取内容
            elif current_story and line.strip() and not line.startswith('#'):
                if line.startswith('🔗'):
                    current_story['url'] = line.replace('🔗', '').strip()
                elif line.startswith('📊 相关性:'):
                    rel_match = re.search(r'(\d+\.?\d*)', line)
                    if rel_match:
                        current_story['relevance_score'] = float(rel_match.group(1))
                elif '📡' in line:
                    current_story['source'] = 'tavily'
                elif '🐦' in line:
                    current_story['source'] = 'twitter'
                elif not line.startswith('---') and not current_story['content']:
                    current_story['content'] = line.strip()
        
        if current_story:
            stories.append(current_story)
        
        return stories
    
    def generate_viral_scripts(self, briefing_path: str, output_path: str, top_n: int = 3):
        """生成爆款视频脚本"""
        # 分析新闻
        scored_stories = self.analyze_briefing(briefing_path)
        
        if not scored_stories:
            print("❌ 没有找到合适的新闻")
            return
        
        # 取top N
        top_stories = scored_stories[:top_n]
        
        print(f"\n🎬 生成 {len(top_stories)} 个爆款脚本...")
        
        # 生成脚本
        scripts = []
        for i, story in enumerate(top_stories, 1):
            print(f"\n📝 脚本 {i}: {story['title'][:30]}...")
            print(f"   爆点分数: {story['viral_score']:.1f}")
            print(f"   主要原因: {', '.join(story['viral_reasons'][:2])}")
            
            script = self.generate_viral_script(
                story,
                story['viral_score'],
                story['viral_reasons']
            )
            scripts.append(script)
        
        # 保存
        self._save_scripts(scripts, output_path)
        
        print(f"\n✅ 爆款脚本已生成: {output_path}")
    
    def _save_scripts(self, scripts: List[Dict], output_path: str):
        """保存脚本"""
        now = datetime.now()
        md = f"# 🔥 爆款视频脚本 {now.strftime('%Y-%m-%d')}\n\n"
        md += f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M')} GMT+8\n"
        md += f"> 基于爆点识别算法自动筛选\n"
        md += f"> 脚本数量：{len(scripts)} 个\n\n"
        md += "---\n\n"
        
        for i, script in enumerate(scripts, 1):
            md += f"## 🔥 脚本 {i}: {script['标题']}\n\n"
            md += f"**爆点分数**: {script['爆点分数']} | **预估流量**: {script['预估流量']}\n\n"
            md += f"**爆点原因**: {', '.join(script['爆点原因'])}\n\n"
            
            md += "### 📜 脚本内容\n\n```\n"
            md += script['脚本']
            md += "\n```\n\n"
            
            md += "### 🎨 视觉建议\n\n"
            for visual in script['视觉建议']:
                md += f"- {visual}\n"
            md += "\n"
            
            md += f"### 🎵 BGM建议\n\n{script['BGM建议']}\n\n"
            
            md += "### 📝 字幕时间轴\n\n"
            md += "| 时间 | 文字 | 大小 | 颜色 | 特效 |\n"
            md += "|------|------|------|------|------|\n"
            for sub in script['字幕']:
                md += f"| {sub['时间']} | {sub['文字']} | {sub['大小']} | {sub['颜色']} | {sub['特效']} |\n"
            md += "\n"
            
            md += f"### 🔗 原始来源\n\n{script['原始链接']}\n\n"
            md += "---\n\n"
        
        md += "## 💡 爆款制作技巧\n\n"
        md += "1. **前3秒决定生死**: 必须用最强的视觉冲击\n"
        md += "2. **字幕要大要醒目**: 红色/黄色，加特效\n"
        md += "3. **快速剪辑**: 0.5-1秒一个镜头，保持紧张感\n"
        md += "4. **BGM要刺激**: 节奏快、有冲击力\n"
        md += "5. **结尾强CTA**: \"关注我\"要闪烁、放大\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)
        
        # 同时保存JSON
        json_path = output_path.replace('.md', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)


def main():
    print("🚀 启动爆点新闻识别器...")
    
    detector = ViralNewsDetector()
    
    # 使用最新简报
    now = datetime.now()
    briefing_path = f"/Users/haoc/.openclaw/workspace/briefing-{now.strftime('%Y-%m-%d')}-enhanced.md"
    output_path = f"/Users/haoc/.openclaw/workspace/viral-scripts-{now.strftime('%Y-%m-%d')}.md"
    
    try:
        detector.generate_viral_scripts(briefing_path, output_path, top_n=3)
    except FileNotFoundError:
        print(f"❌ 找不到简报文件: {briefing_path}")
        print("💡 请先运行: python3 enhanced-news-aggregator.py")
        return
    
    print("\n🎉 完成！这些是今天最有流量潜力的新闻")


if __name__ == "__main__":
    main()
