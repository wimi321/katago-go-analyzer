#!/usr/bin/env python3
"""
智能新闻聚合器 - 多源搜索与质量筛选
"""

import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Set
from collections import defaultdict

class NewsAggregator:
    def __init__(self):
        self.results = []
        self.seen_urls = set()
        
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
                    # 解析用户名
                    parts = line.split('(')
                    if len(parts) >= 2:
                        current_tweet = {
                            'username': parts[0].strip(),
                            'display_name': parts[1].split(')')[0] if ')' in parts[1] else ''
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
            print(f"Twitter搜索失败: {e}")
            return []
    
    def calculate_relevance_score(self, tweet: Dict, keywords: List[str]) -> float:
        """计算相关性得分"""
        text = tweet.get('text', '').lower()
        score = 0.0
        
        # 关键词匹配
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1.0
        
        # 长度惩罚（过短可能是spam）
        if len(text) < 50:
            score *= 0.5
        
        # URL存在加分
        if tweet.get('url'):
            score += 0.5
            
        return score
    
    def deduplicate(self, tweets: List[Dict]) -> List[Dict]:
        """去重"""
        unique = []
        for tweet in tweets:
            url = tweet.get('url', '')
            if url and url not in self.seen_urls:
                self.seen_urls.add(url)
                unique.append(tweet)
        return unique
    
    def aggregate_by_category(self) -> Dict[str, List[Dict]]:
        """按类别聚合搜索"""
        categories = {
            "AI突破": [
                "DeepSeek R1", "Claude Opus", "GPT-5", "Gemini 3",
                "AI breakthrough", "AI模型"
            ],
            "科技公司": [
                "OpenAI", "Anthropic", "Google AI", "Meta AI",
                "Microsoft AI", "Apple Intelligence"
            ],
            "政策经济": [
                "Trump tariff", "特朗普关税", "中美贸易",
                "经济数据", "policy change"
            ],
            "加密货币": [
                "Bitcoin", "Ethereum", "crypto", "Web3",
                "DeFi", "NFT"
            ]
        }
        
        results = defaultdict(list)
        
        for category, keywords in categories.items():
            print(f"\n🔍 搜索类别: {category}")
            
            # 构建搜索查询
            query = " OR ".join([f'"{kw}"' for kw in keywords[:3]])  # 限制查询长度
            
            tweets = self.search_twitter(query, count=15)
            
            # 计算相关性并排序
            scored_tweets = []
            for tweet in tweets:
                score = self.calculate_relevance_score(tweet, keywords)
                if score > 0:
                    tweet['relevance_score'] = score
                    scored_tweets.append(tweet)
            
            # 排序并去重
            scored_tweets.sort(key=lambda x: x['relevance_score'], reverse=True)
            unique_tweets = self.deduplicate(scored_tweets)
            
            # 取top 5
            results[category] = unique_tweets[:5]
            print(f"  ✓ 找到 {len(unique_tweets)} 条相关推文")
        
        return results
    
    def generate_briefing(self, categorized_results: Dict[str, List[Dict]]) -> str:
        """生成简报"""
        now = datetime.now()
        briefing = f"# 📰 每日简报 {now.strftime('%Y-%m-%d')}\n\n"
        briefing += f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M')} GMT+8\n"
        briefing += f"> 数据来源：X/Twitter 智能聚合\n"
        briefing += f"> 搜索策略：分类关键词 + 相关性排序\n\n"
        briefing += "---\n\n"
        
        category_icons = {
            "AI突破": "🤖",
            "科技公司": "🏢",
            "政策经济": "📊",
            "加密货币": "💰"
        }
        
        for category, tweets in categorized_results.items():
            if not tweets:
                continue
                
            icon = category_icons.get(category, "📌")
            briefing += f"## {icon} {category}\n\n"
            
            for i, tweet in enumerate(tweets, 1):
                text = tweet.get('text', '')[:200]  # 限制长度
                username = tweet.get('username', 'Unknown')
                url = tweet.get('url', '')
                timestamp = tweet.get('timestamp', '')
                score = tweet.get('relevance_score', 0)
                
                briefing += f"### {i}. @{username}\n"
                briefing += f"{text}\n\n"
                if url:
                    briefing += f"🔗 [{url}]({url})\n"
                briefing += f"📅 {timestamp} | 相关性: {score:.1f}\n\n"
            
            briefing += "---\n\n"
        
        briefing += "## 💡 搜索质量报告\n\n"
        total_results = sum(len(tweets) for tweets in categorized_results.values())
        briefing += f"- 总结果数: {total_results}\n"
        briefing += f"- 去重后: {len(self.seen_urls)}\n"
        briefing += f"- 覆盖类别: {len([c for c, t in categorized_results.items() if t])}\n\n"
        
        briefing += "*本简报使用智能聚合算法生成，已优化关键词策略和相关性排序*\n"
        
        return briefing


def main():
    print("🚀 启动智能新闻聚合器...")
    
    aggregator = NewsAggregator()
    
    # 按类别聚合
    results = aggregator.aggregate_by_category()
    
    # 生成简报
    briefing = aggregator.generate_briefing(results)
    
    # 保存文件
    now = datetime.now()
    filename = f"/Users/haoc/.openclaw/workspace/briefing-{now.strftime('%Y-%m-%d')}-v2.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(briefing)
    
    print(f"\n✅ 简报已生成: {filename}")
    print(f"📊 总计 {sum(len(t) for t in results.values())} 条高质量结果")


if __name__ == "__main__":
    main()
