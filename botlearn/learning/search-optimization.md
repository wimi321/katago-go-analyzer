# 搜索优化学习笔记

## 问题诊断 (2026-02-11)

李行反馈："你搜索一直感觉都不行"

### 当前搜索策略分析

**现有方法：**
1. ❌ Brave Search API - 未配置
2. ✅ X/Twitter (bird) - 可用但结果质量不稳定
3. ❌ web_fetch - 对动态网站支持差

**问题根源：**
- 关键词选择过于宽泛（"AI OR 人工智能 OR 科技"）
- 缺乏时间过滤和相关性排序
- 依赖单一数据源（Twitter）
- 没有结果去重和质量筛选

---

## 搜索优化策略

### 1. 多层次关键词策略

**原则：从具体到一般**

```
Level 1 (高精度): 
- "DeepSeek R1" "Claude Opus 4" "GPT-5"
- "特朗普关税" "中美贸易"

Level 2 (中精度):
- "AI breakthrough" "科技突破"
- "政策变化" "经济数据"

Level 3 (广泛):
- "AI" "tech" "科技"
```

### 2. 时间窗口控制

**Twitter搜索加时间过滤：**
```bash
# 最近24小时
bird search "DeepSeek" -n 20 --since "2026-02-10"

# 最近1小时（热点）
bird search "breaking news" -n 10 --since "1h"
```

### 3. 多源聚合

**数据源优先级：**
1. **实时热点**: Twitter (bird)
2. **深度内容**: RSS feeds (需配置)
3. **技术资讯**: Hacker News API
4. **通用搜索**: Brave Search (需配置API key)

### 4. 结果质量筛选

**筛选维度：**
- 转发/点赞数（Twitter engagement）
- 作者权威性（verified账号）
- 内容长度（过滤spam）
- 关键词密度

---

## 实施计划

### Phase 1: 优化现有Twitter搜索 ✅

**改进点：**
```python
# 分类搜索而非混合
categories = {
    "AI突破": ["DeepSeek R1", "Claude Opus", "GPT-5", "Gemini"],
    "科技公司": ["OpenAI", "Anthropic", "Google AI", "Meta AI"],
    "政策经济": ["特朗普", "关税", "中美", "经济数据"],
    "加密货币": ["Bitcoin", "Ethereum", "Web3"]
}

# 每个类别独立搜索，取top 5
# 按engagement排序
# 去重（URL/内容相似度）
```

### Phase 2: 配置Brave Search API

```bash
# 获取API key: https://brave.com/search/api/
openclaw configure --section web
# 输入 BRAVE_API_KEY
```

### Phase 3: 集成RSS源

**推荐源：**
- Hacker News: https://news.ycombinator.com/rss
- TechCrunch: https://techcrunch.com/feed/
- Ars Technica: https://arstechnica.com/feed/
- 36氪: https://36kr.com/feed

### Phase 4: 构建聚合管道

```
[Twitter实时] → 
[RSS深度] → 
[Brave补充] → 
[去重排序] → 
[分类整理] → 
[生成简报]
```

---

## 搜索质量评估标准

### 好的搜索结果应该：

✅ **相关性高**: 90%+ 内容与主题直接相关  
✅ **时效性强**: 80%+ 内容来自最近24小时  
✅ **信息密度**: 每条结果包含实质性信息（非spam）  
✅ **多样性**: 覆盖不同角度和来源  
✅ **可验证**: 包含原始链接和时间戳  

### 当前问题：

❌ 相关性: ~60%（太多噪音）  
❌ 时效性: 无法保证（Twitter算法排序）  
❌ 信息密度: ~40%（大量低质量推文）  
✅ 多样性: 尚可  
✅ 可验证: 良好  

---

## 参考资料

### Boolean Search 技巧

```
# Twitter高级搜索
"exact phrase" - 精确匹配
keyword1 OR keyword2 - 任一匹配
keyword1 -keyword2 - 排除
from:username - 特定用户
min_faves:100 - 最少点赞数
```

### API限流策略

- Twitter: 15 requests / 15 min
- Brave Search: 根据套餐
- 建议：缓存结果，避免重复查询

---

## 下一步行动

1. [ ] 实现分类搜索脚本
2. [ ] 配置Brave Search API
3. [ ] 测试RSS聚合
4. [ ] 建立质量评分系统
5. [ ] 优化简报生成流程

---

*记录时间: 2026-02-11 00:10*
