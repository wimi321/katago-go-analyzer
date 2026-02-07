# KataGo 分析器使用说明

## 快速开始

```python
from katago_analyzer import KataGoAnalyzer, Color

# 初始化
analyzer = KataGoAnalyzer(
    model_path="/Users/haoc/.katago/models/kata1-b28c512nbt-s12374138624-d5703190512.bin.gz"
)

if analyzer.start():
    # 分析当前局面
    results = analyzer.analyze(Color.WHITE, visits=100)
    
    # 打印结果
    for i, move in enumerate(results):
        print(f"{i+1}. {move.move} - 胜率: {move.winrate*100:.1f}%")
    
    analyzer.stop()
```

## 核心功能

### 1. 基本操作
```python
# 设置棋盘
analyzer.set_board_size(19)
analyzer.set_komi(7.5)
analyzer.clear_board()

# 下棋
analyzer.play(Color.BLACK, "Q16")
analyzer.play(Color.WHITE, "D4")

# 悔棋
analyzer.undo()
```

### 2. 分析
```python
# 分析局面，返回最佳着法列表
results = analyzer.analyze(Color.WHITE, visits=200)

# 获取最佳着法
best_move = analyzer.get_best_move(Color.WHITE, visits=200)

# 比较多个候选着法
moves = ["R4", "Q4", "P4"]
comparison = analyzer.compare_moves(Color.WHITE, moves, visits=100)
```

### 3. 分析结果结构
```python
@dataclass
class MoveAnalysis:
    move: str           # 着手 (如 "Q16")
    visits: int         # 搜索次数
    winrate: float      # 胜率 (0-1)
    score_lead: float   # 领先目数
    policy: float       # 策略概率
    pv: List[str]       # 主要变化
```

## GTP 命令

### 基础命令
| 命令 | 说明 |
|------|------|
| `protocol_version` | GTP 协议版本 |
| `list_commands` | 所有可用命令 |
| `boardsize 19` | 设置19路棋盘 |
| `clear_board` | 清空棋盘 |
| `play B Q16` | 黑下Q16 |
| `genmove W` | 白落子 |
| `undo` | 悔棋 |
| `quit` | 退出 |

### 分析命令
| 命令 | 说明 |
|------|------|
| `kata-analyze B 100` | 分析当前局面，黑方，100次搜索 |
| `lz-analyze W 100` | Lizzie 风格分析 |
| `kata-genmove_analyze B 100` | 生成着法并分析 |
| `kata-search_analyze B 100` | 搜索并分析 |
| `stop` | 停止分析 |

## 命令行使用

```bash
# 直接运行演示
python3 katago_analyzer.py
```

## 输出示例

```
分析当前局面 (执白):
  1. R4     visits=25   winrate=52.3%   score=-0.5   policy=8.2%
  2. Q4     visits=22   winrate=51.8%   score=-0.3   policy=7.5%
  3. P4     visits=18   winrate=50.2%   score=+0.1   policy=6.1%
```

## 注意事项

1. **模型文件**: 需要下载 KataGo 模型 (约 259MB)
2. **配置文件**: 使用 KataGo 自带的 gtp_example.cfg
3. **性能**: b28 模型在 M4 Pro 上约需 10-20 秒完成 100 次搜索
