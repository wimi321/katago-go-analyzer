#!/usr/bin/env python3
"""
围棋规则分析模块
- 基础规则：气的计算
- 简单形势判断
- 建议选点
"""

import re
from collections import defaultdict


def parse_sgf(sgf_content):
    """解析SGF"""
    moves = []
    # 提取所有B和W落子
    for match in re.finditer(r'([BW])\[([a-t]{2})\]', sgf_content):
        color = 'B' if match.group(1) == 'B' else 'W'
        col = ord(match.group(2)[0]) - ord('a')
        row = ord(match.group(2)[1]) - ord('a')
        moves.append((color, row, col))
    return moves


class GoAnalyzer:
    """围棋分析器"""
    
    def __init__(self, board_size=19):
        self.size = board_size
        self.directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    def init_board(self):
        """初始化棋盘"""
        self.board = [['.' for _ in range(self.size)] for _ in range(self.size)]
    
    def place_stone(self, row, col, color):
        """放置棋子"""
        if 0 <= row < self.size and 0 <= col < self.size:
            self.board[row][col] = color
    
    def apply_moves(self, moves):
        """执行所有落子"""
        self.init_board()
        for color, row, col in moves:
            self.place_stone(row, col, color)
    
    def count_liberties(self, row, col, visited=None):
        """计算气"""
        if visited is None:
            visited = set()
        
        color = self.board[row][col]
        if color == '.':
            return 0
        
        stack = [(row, col)]
        liberties = set()
        group = set()
        
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            group.add((r, c))
            
            for dr, dc in self.directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if self.board[nr][nc] == '.':
                        liberties.add((nr, nc))
                    elif self.board[nr][nc] == color and (nr, nc) not in group:
                        stack.append((nr, nc))
        
        return len(liberties), group
    
    def remove_dead_stones(self):
        """提吃死子"""
        removed = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] != '.':
                    libs, group = self.count_liberties(r, c)
                    if libs == 0:
                        for (gr, gc) in group:
                            self.board[gr][gc] = '.'
                            removed.append((gr, gc))
        return removed
    
    def analyze(self):
        """完整分析"""
        self.remove_dead_stones()
        
        # 统计
        black_count = white_count = 0
        black_territory = white_territory = 0
        black_stones = []
        white_stones = []
        empty_points = []
        
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 'B':
                    black_count += 1
                    black_stones.append((r, c))
                elif self.board[r][c] == 'W':
                    white_count += 1
                    white_stones.append((r, c))
                else:
                    empty_points.append((r, c))
        
        # 计算每颗棋子的气
        black_liberties = []
        white_liberties = []
        for r, c in black_stones:
            libs, _ = self.count_liberties(r, c)
            black_liberties.append(libs)
        for r, c in white_stones:
            libs, _ = self.count_liberties(r, c)
            white_liberties.append(libs)
        
        # 分析建议（简单规则）
        suggestions = self.suggest_moves(empty_points)
        
        return {
            'black_count': black_count,
            'white_count': white_count,
            'black_liberties': {
                'avg': sum(black_liberties) / len(black_liberties) if black_liberties else 0,
                'min': min(black_liberties) if black_liberties else 0
            },
            'white_liberties': {
                'avg': sum(white_liberties) / len(white_liberties) if white_liberties else 0,
                'min': min(white_liberties) if white_liberties else 0
            },
            'suggestions': suggestions[:5],  # 前5个建议
            'board': self.board
        }
    
    def suggest_moves(self, empty_points):
        """建议下一手（简单规则）"""
        suggestions = []
        
        for r, c in empty_points:
            score = 0
            
            # 检查周围棋子
            neighbors = []
            for dr, dc in self.directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    neighbors.append(self.board[nr][nc])
            
            # 1. 扩大己方领地
            if 'B' in neighbors and 'W' not in neighbors:
                score += 2  # 扩张黑棋
            
            # 2. 攻击对方弱棋
            if 'W' in neighbors:
                # 检查是否威胁对方棋子
                score += 1
            
            # 3. 补强己方弱棋
            if 'B' in neighbors:
                score += 1  # 简单加分，不计算气的逻辑了
            
            # 4. 中心价值
            center = self.size // 2
            dist_from_center = abs(r - center) + abs(c - center)
            score += (self.size - dist_from_center) * 0.1
            
            if score > 0:
                suggestions.append((score, r, c))
        
        # 按分数排序
        suggestions.sort(reverse=True)
        return suggestions
    
    def generate_report(self, analysis):
        """生成分析报告"""
        lines = [
            "📊 **围棋局面分析报告**",
            "",
            "**棋子统计:**",
            f"⚫ 黑子: {analysis['black_count']}",
            f"⚪ 白子: {analysis['white_count']}",
            "",
            "**气数分析:**",
            f"黑子平均气数: {analysis['black_liberties']['avg']:.1f}",
            f"白子平均气数: {analysis['white_liberties']['avg']:.1f}",
            "",
            "**建议选点 (AI推荐):**"
        ]
        
        for i, (score, r, c) in enumerate(analysis['suggestions']):
            col_letter = chr(ord('a') + c)
            row_letter = chr(ord('a') + r)
            lines.append(f"{i+1}. {col_letter}{row_letter} (评分: {score:.1f})")
        
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    
    # 测试
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            sgf = f.read()
    else:
        sgf = open("/Users/haoc/.openclaw/workspace/test_v2.sgf").read()
    
    # 解析并分析
    moves = parse_sgf(sgf)
    analyzer = GoAnalyzer()
    analyzer.apply_moves(moves)
    analysis = analyzer.analyze()
    
    # 打印报告
    print(analyzer.generate_report(analysis))
