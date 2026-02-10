#!/usr/bin/env python3
"""
增强版新闻聚合器 - 集成 Tavily API
支持多源搜索：Tavily (深度) + Twitter (实时)
"""

import json
import subprocess
import os
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

class EnhancedNewsAggregator:
    def __init__(self):
        self.results = []
        self.seen_urls = set()
        self.tavily_available = bool(os.getenv('TAVILY_API_KEY'))
        
    def search_tavily(self, query: str, topic: str = "news", days: int = 3) -> List[Dict]:
        """使用Tavily搜索（AI优化的搜索引擎）"""
        if not self.tavily_available:
            print(f"  ⚠️  Tavily API未配置，跳过")
            return []
            
        try:
            cmd = [
                "node",
                "/Users/haoc/.openclaw/workspace/skills/tavily-search/scripts/search.mjs",
                query,
                "-n", "5",
                "--topic", topic
            ]
            
            if topic == "news":
                cmd.extend(["--days", str(days)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"  ⚠️  Tavily搜索失败: {result.stderr[:100]}")
                return []
            
            # 解析Tavily输出
            articles = []
            lines = result.stdout.split('\n')
            current_article = {}
            in_sources = False
            
            for line in lines:
                if line.strip() == "## Sources":
                    in_sources = True
                    continue
                    
                if not in_sources:
                    continue
                
                if line.startswith('- **') and '**' in line[4:]:
                    if current_article:
                        articles.append(current_article)
                    
                    # 解析标题和相关性
                    title_end = line.find('**', 4)
                    title = line[4:title_end]
                    
                    relevance = 100
                    if 'relevance:' in line:
                        try:
                            rel_str = line.split('relevance:')[1].split('%')[0].strip()
                            relevance = int(rel_str)
                        except:
                            pass
                    
                    current_article = {
                        'title': title,
                        'relevance_score': relevance / 100.0,
                        'source': 'tavily'
                    }
                    
                elif line.strip().startswith('http') and current_article:
                    current_article['url'] = line.strip()
                    
                elif line.strip() and not line.startswith('#') and current_article and 'text' not in current_article:
                    current_article['text'] = line.strip()
            
            if current_article:
                articles.append(current_article)
            
            return articles
            
        except Exception as e:
            print(f"  ⚠️  Tavily搜索异常: {e}")
            return []
    
    def search_twitter(self, query: str, count: int = 10) -> List[Dict]:
        """使用bird搜索Twitter"""
        try:
            cmd = ["bird", "search", query, "-n", str(count)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            # 解析bird输出
            tweets = []
            lines = result.stdout.split('\n')
            current_tweet = {}
            
            for line in lines:
                if line.startswith('@'):
                    if current_tweet:
                        tweets.append(current_tweet)
                    parts = line.split('(')
                    if len(parts) >= 2:
                        current_tweet = {
                            'username': parts[0].strip(),
                            'display_name': parts[1].split(')')[0] if ')' in parts[1] else '',
                            'source': 'twitter'
                        }
                elif line.startswith('📅'):
                    current_tweet['timestamp'] = line.replace('📅', '').strip()
                elif line.startswith('🔗'):
                    current_tweet['url'] = line.replace('🔗', '').strip()
                elif line.strip() and not line.startswith('─'):
                    if 'text' not in current_tweet:
                        current_tweet['text'] = line.strip()
                    else:
                        current_tweet['text'] += ' ' + line.strip()
            
            if current_tweet:
                tweets.append(current_tweet)
                
            return tweets
            
        except Exception as e:
            print(f"  ⚠️  Twitter搜索失败: {e}")
            return []
    
    def calculate_relevance_score(self, item: Dict, keywords: List[str]) -> float:
        """计算相关性得分"""
        # Tavily结果已有相关性分数
        if item.get('source') == 'tavily' and 'relevance_score' in item:
            return item['relevance_score']
        
        # Twitter结果需要计算
        text = item.get('text', '').lower()
        score = 0.0
        
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1.0
        
        if len(text) < 50:
            score *= 0.5
        
        if item.get('url'):
            score += 0.5
            
        return score
    
    def deduplicate(self, items: List[Dict]) -> List[Dict]:
        """去重"""
        unique = []
        for item in items:
            url = item.get('url', '')
            if url and url not in self.seen_urls:
                self.seen_urls.add(url)
                unique.append(item)
        return unique
    
    def aggregate_by_category(self) -> Dict[str, List[Dict]]:
        """按类别聚合搜索 - Tavily优先，Twitter补充"""
        categories = {
            "AI突破": {
                "tavily_query": "AI breakthrough DeepSeek Claude GPT-5 2026",
                "twitter_keywords": ["DeepSeek R1", "Claude Opus", "GPT-5", "Gemini 3"]
            },
            "科技公司": {
                "tavily_query": "tech companies AI OpenAI Anthropic Google 2026",
                "twitter_keywords": ["OpenAI", "Anthropic", "Google AI", "Meta AI"]
            },
            "政策经济": {
                "tavily_query": "Trump tariff policy China trade 2026",
                "twitter_keywords": ["Trump tariff", "特朗普关税", "中美贸易"]
            },
            "加密货币": {
                "tavily_query": "cryptocurrency Bitcoin Ethereum Web3 2026",
                "twitter_keywords": ["Bitcoin", "Ethereum", "crypto", "Web3"]
            }
        }
        
        results = defaultdict(list)
        
        for category, config in categories.items():
            print(f"\n🔍 搜索类别: {category}")
            
            all_items = []
            
            # 1. Tavily搜索（深度内容）
            if self.tavily_available:
                print(f"  📡 Tavily搜索...")
                tavily_results = self.search_tavily(config['tavily_query'], topic="news", days=3)
                all_items.extend(tavily_results)
                print(f"    ✓ Tavily: {len(tavily_results)} 条")
            
            # 2. Twitter搜索（实时动态）
            print(f"  🐦 Twitter搜索...")
            twitter_query = " OR ".join([f'"{kw}"' for kw in config['twitter_keywords'][:3]])
            twitter_results = self.search_twitter(twitter_query, count=10)
            all_items.extend(twitter_results)
            print(f"    ✓ Twitter: {len(twitter_results)} 条")
            
            # 3. 计算相关性并排序
            scored_items = []
            for item in all_items:
                score = self.calculate_relevance_score(item, config['twitter_keywords'])
                if score > 0:
                    item['relevance_score'] = score
                    scored_items.append(item)
            
            scored_items.sort(key=lambda x: x['relevance_score'], reverse=True)
            unique_items = self.deduplicate(scored_items)
            
            # 取top 5
            results[category] = unique_items[:5]
            print(f"  ✅ 最终: {len(unique_items)} 条去重结果")
        
        return results
    
    def generate_briefing(self, categorized_results: Dict[str, List[Dict]]) -> str:
        """生成简报"""
        now = datetime.now()
        briefing = f"# 📰 每日简报 {now.strftime('%Y-%m-%d')}\n\n"
        briefing += f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M')} GMT+8\n"
        briefing += f"> 数据来源：Tavily AI Search + X/Twitter\n"
        briefing += f"> 搜索策略：深度内容(Tavily) + 实时动态(Twitter)\n\n"
        briefing += "---\n\n"
        
        category_icons = {
            "AI突破": "🤖",
            "科技公司": "🏢",
            "政策经济": "📊",
            "加密货币": "💰"
        }
        
        for category, items in categorized_results.items():
            if not items:
                continue
                
            icon = category_icons.get(category, "📌")
            briefing += f"## {icon} {category}\n\n"
            
            for i, item in enumerate(items, 1):
                source_icon = "📡" if item.get('source') == 'tavily' else "🐦"
                title = item.get('title', item.get('display_name', 'Unknown'))
                text = item.get('text', '')[:250]
                url = item.get('url', '')
                score = item.get('relevance_score', 0)
                
                briefing += f"### {i}. {source_icon} {title}\n"
                briefing += f"{text}\n\n"
                if url:
                    briefing += f"🔗 {url}\n"
                briefing += f"📊 相关性: {score:.1f}\n\n"
            
            briefing += "---\n\n"
        
        briefing += "## 💡 搜索质量报告\n\n"
        total_results = sum(len(items) for items in categorized_results.values())
        tavily_count = sum(1 for items in categorized_results.values() for item in items if item.get('source') == 'tavily')
        twitter_count = sum(1 for items in categorized_results.values() for item in items if item.get('source') == 'twitter')
        
        briefing += f"- 总结果数: {total_results}\n"
        briefing += f"- Tavily深度内容: {tavily_count}\n"
        briefing += f"- Twitter实时动态: {twitter_count}\n"
        briefing += f"- 去重后URL: {len(self.seen_urls)}\n"
        briefing += f"- 覆盖类别: {len([c for c, t in categorized_results.items() if t])}\n\n"
        
        briefing += "*本简报使用 Tavily AI Search + Twitter 双源聚合，已优化搜索质量*\n"
        
        return briefing


def main():
    print("🚀 启动增强版新闻聚合器...")
    print(f"📡 Tavily API: {'✅ 已配置' if os.getenv('TAVILY_API_KEY') else '❌ 未配置'}")
    
    aggregator = EnhancedNewsAggregator()
    
    # 按类别聚合
    results = aggregator.aggregate_by_category()
    
    # 生成简报
    briefing = aggregator.generate_briefing(results)
    
    # 保存文件
    now = datetime.now()
    filename = f"/Users/haoc/.openclaw/workspace/briefing-{now.strftime('%Y-%m-%d')}-enhanced.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(briefing)
    
    print(f"\n✅ 简报已生成: {filename}")
    print(f"📊 总计 {sum(len(t) for t in results.values())} 条高质量结果")


if __name__ == "__main__":
    main()
