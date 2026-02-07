#!/usr/bin/env python3
"""
KataGo 分析器 - Python 封装
支持 GTP 协议和 JSON 格式分析输出
"""

import subprocess
import threading
import json
import time
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

class Color(Enum):
    BLACK = "B"
    WHITE = "W"

@dataclass
class MoveAnalysis:
    """单步分析结果"""
    move: str           # 着手 (如 "Q16")
    visits: int         # 搜索次数
    winrate: float      # 胜率 (0-1)
    score_lead: float   # 领先目数
    policy: float       # 策略概率
    pv: List[str] = field(default_factory=list)  # 主要变化
    lz_winrate: Optional[float] = None
    order: int = 0

@dataclass
class BoardState:
    """棋盘状态"""
    board_size: int = 19
    komi: float = 7.5
    turn: Color = Color.BLACK
    move_history: List[str] = field(default_factory=list)
    black_prisoners: int = 0
    white_prisoners: int = 0

class KataGoAnalyzer:
    """KataGo 分析器封装"""
    
    def __init__(self, 
                 model_path: str,
                 config_path: str = "/tmp/katago.cfg",
                 config_overrides: Optional[Dict[str, Any]] = None):
        """
        初始化
        
        Args:
            model_path: 模型文件路径 (.bin.gz)
            config_path: 配置文件路径 (可选)
            config_overrides: 配置覆盖项
        """
        self.model_path = model_path
        self.config_path = config_path
        self.config_overrides = config_overrides or {}
        self.proc: Optional[subprocess.Popen] = None
        self.is_ready = False
        
import shutil
import subprocess
import threading
import json
import time
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

class Color(Enum):
    BLACK = "B"
    WHITE = "W"

@dataclass
class MoveAnalysis:
    """单步分析结果"""
    move: str           # 着手 (如 "Q16")
    visits: int         # 搜索次数
    winrate: float      # 胜率 (0-1)
    score_lead: float   # 领先目数
    policy: float       # 策略概率
    pv: List[str] = field(default_factory=list)  # 主要变化
    lz_winrate: Optional[float] = None
    order: int = 0

@dataclass
class BoardState:
    """棋盘状态"""
    board_size: int = 19
    komi: float = 7.5
    turn: Color = Color.BLACK
    move_history: List[str] = field(default_factory=list)
    black_prisoners: int = 0
    white_prisoners: int = 0

class KataGoAnalyzer:
    """KataGo 分析器封装"""
    
    def __init__(self, 
                 model_path: str,
                 config_path: str = "/tmp/katago.cfg",
                 config_overrides: Optional[Dict[str, Any]] = None):
        """
        初始化
        
        Args:
            model_path: 模型文件路径 (.bin.gz)
            config_path: 配置文件路径 (可选)
            config_overrides: 配置覆盖项
        """
        self.model_path = model_path
        self.config_path = config_path
        self.config_overrides = config_overrides or {}
        self.proc: Optional[subprocess.Popen] = None
        self.is_ready = False
        
    def start(self, timeout: float = 30.0) -> bool:
        """启动 KataGo 引擎"""
        cmd = ['/opt/homebrew/bin/katago', 'gtp']
        
        if self.config_path:
            cmd.extend(['-config', self.config_path])
        
        cmd.extend(['-model', self.model_path])
        
        # 添加配置覆盖
        if self.config_overrides:
            overrides = ','.join([f"{k}={v}" for k, v in self.config_overrides.items()])
            cmd.extend(['-override-config', overrides])
        
        print(f"启动 KataGo: {' '.join(cmd)}")
        
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # 等待初始化
            time.sleep(2)
            
            # 验证就绪
            response = self._send_command('protocol_version')
            if response and response.startswith('='):
                self.is_ready = True
                print("✓ KataGo 引擎就绪")
                return True
            
            # 检查 stderr
            stderr = self._read_stderr()
            print(f"初始化错误: {stderr}")
            
        except Exception as e:
            print(f"启动失败: {e}")
        
        return False
    
    def stop(self):
        """停止引擎"""
        if self.proc:
            try:
                self.proc.stdin.write('quit\n')
                self.proc.stdin.flush()
                self.proc.wait(timeout=5)
            except:
                self.proc.kill()
            self.proc = None
            self.is_ready = False
            print("✓ KataGo 已停止")
    
    def _send_command(self, cmd: str, timeout: float = 5.0) -> str:
        """发送 GTP 命令并获取响应"""
        if not self.proc:
            return ""
        
        self.proc.stdin.write(cmd + '\n')
        self.proc.stdin.flush()
        
        # 读取响应
        lines = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            lines.append(line)
            if line.startswith('=') or line.startswith('?'):
                break
        
        return '\n'.join(lines)
    
    def _read_stderr(self) -> str:
        """读取 stderr"""
        if not self.proc:
            return ""
        
        try:
            # 非阻塞读取
            import select
            if select.select([self.proc.stderr], [], [], 0.1)[0]:
                return self.proc.stderr.read()
        except:
            pass
        return ""
    
    # ============ 基础 GTP 操作 ============
    
    def set_board_size(self, size: int = 19) -> bool:
        """设置棋盘尺寸"""
        response = self._send_command(f'boardsize {size}')
        return response.startswith('=')
    
    def clear_board(self) -> bool:
        """清空棋盘"""
        response = self._send_command('clear_board')
        return response.startswith('=')
    
    def set_komi(self, komi: float = 7.5) -> bool:
        """设置贴目"""
        response = self._send_command(f'komi {komi}')
        return response.startswith('=')
    
    def play(self, color: Color, move: str) -> bool:
        """
        下一手棋
        
        Args:
            color: BLACK 或 WHITE
            move: 坐标 (如 "Q16") 或 "pass"
        """
        response = self._send_command(f'play {color.value} {move}')
        return response.startswith('=')
    
    def undo(self) -> bool:
        """悔棋"""
        response = self._send_command('undo')
        return response.startswith('=')
    
    def genmove(self, color: Color) -> str:
        """
        生成一手棋
        
        Returns:
            最佳着法坐标
        """
        response = self._send_command(f'genmove {color.value}')
        lines = response.split('\n')
        for line in lines:
            if line.startswith('= '):
                return line[2:].strip().split()[0]  # 返回第一个词
        return "pass"
    
    # ============ 分析功能 ============
    
    def analyze(self, 
                color: Color, 
                visits: int = 200,
                verbose: bool = False) -> List[MoveAnalysis]:
        """
        分析当前局面
        
        Args:
            color: 当前执黑/执白
            visits: 搜索次数
            verbose: 详细输出
            
        Returns:
            按优先级排序的分析结果列表
        """
        if not self.is_ready:
            print("引擎未就绪")
            return []
        
        results = []
        
        # 使用 kata-analyze，添加参数使其只输出一次最终结果
        cmd = f'kata-analyze {color.value} {visits}'
        self.proc.stdin.write(cmd + '\n')
        self.proc.stdin.flush()
        
        # 等待分析完成
        import time
        time.sleep(3)
        
        # 收集分析结果
        max_lines = 100
        line_count = 0
        
        while line_count < max_lines:
            try:
                # 使用 poll 检查是否有数据
                if self.proc.stdout.closed:
                    break
                    
                line = self.proc.stdout.readline()
                if not line or line == '':
                    break
                
                line = line.strip()
                line_count += 1
                
                # 检查是否完成
                if line.startswith('=') or line.startswith('?'):
                    break
                
                # 跳过空行
                if not line:
                    continue
                
                # 解析 GTP 扩展格式: info move C17 visits 10 ...
                if line.startswith('info '):
                    analysis = self._parse_gtp_analysis(line)
                    if analysis:
                        results.append(analysis)
                        if verbose:
                            self._print_analysis(analysis, len(results))
                        
            except Exception as e:
                print(f"读取错误: {e}")
                break
        
        # 发送 stop 命令
        self.proc.stdin.write('stop\n')
        self.proc.stdin.flush()
        time.sleep(0.5)
        
        # 消耗剩余输出
        try:
            while True:
                if self.proc.stdout.closed:
                    break
                line = self.proc.stdout.readline()
                if not line or line.strip() == '':
                    break
        except:
            pass
        
        # 按 order 排序
        results.sort(key=lambda x: x.order if x.order >= 0 else 999)
        return results[:10]
    
    def _parse_gtp_analysis(self, line: str) -> Optional[MoveAnalysis]:
        """解析 GTP 扩展格式的分析结果"""
        try:
            # 格式: info move C17 visits 10 winrate 0.95 scoreLead 13.5 ...
            parts = line.split()
            
            data = {}
            i = 1
            while i < len(parts):
                key = parts[i]
                value = parts[i + 1] if i + 1 < len(parts) else ''
                data[key] = value
                i += 2
            
            # 提取关键字段
            move = data.get('move', '')
            if not move or move == 'pass':
                return None
            
            visits = int(data.get('visits', 0))
            winrate = float(data.get('winrate', 0.5))
            score_lead = float(data.get('scoreLead', 0.0))
            prior = float(data.get('prior', 0.0))
            order = int(data.get('order', 0))
            
            # 提取 PV
            pv = []
            pv_start = line.find('pv ')
            if pv_start != -1:
                pv_str = line[pv_start + 3:].split()[0]
                pv = pv_str.split() if pv_str else []
            
            return MoveAnalysis(
                move=move,
                visits=visits,
                winrate=winrate,
                score_lead=score_lead,
                policy=prior,
                pv=pv,
                order=order
            )
            
        except Exception as e:
            print(f"解析错误: {e} in: {line[:50]}")
            return None
    
    def _print_analysis(self, analysis: MoveAnalysis, idx: int):
        """打印分析结果"""
        winrate_pct = analysis.winrate * 100
        print(f"  {idx}. {analysis.move:4s}  "
              f"visits={analysis.visits:4d}  "
              f"winrate={winrate_pct:5.1f}%  "
              f"score={analysis.score_lead:+6.1f}  "
              f"policy={analysis.policy*100:5.2f}%")
    
    # ============ 便捷分析函数 ============
    
    def analyze_position(self, 
                         board_state: BoardState,
                         visits: int = 200) -> List[MoveAnalysis]:
        """
        分析指定局面
        
        Args:
            board_state: 棋盘状态
            visits: 搜索次数
            
        Returns:
            分析结果列表
        """
        # 设置棋盘
        self.clear_board()
        self.set_komi(board_state.komi)
        
        # 复盘
        for move in board_state.move_history:
            color = Color.BLACK if len(move) % 2 == 1 else Color.WHITE
            self.play(color, move)
        
        # 分析
        return self.analyze(board_state.turn, visits=visits)
    
    def get_best_move(self, 
                       color: Color, 
                       visits: int = 200) -> Optional[str]:
        """获取最佳着法"""
        results = self.analyze(color, visits=visits)
        if results:
            return results[0].move
        return None
    
    def compare_moves(self, 
                      color: Color,
                      moves: List[str],
                      visits: int = 200) -> Dict[str, MoveAnalysis]:
        """
        比较多个着法
        
        Args:
            color: 执子颜色
            moves: 要比较的着法列表
            visits: 搜索次数
            
        Returns:
            各着法的分析结果
        """
        results = {}
        
        for move in moves:
            # 下这手棋
            self.play(color, move)
            
            # 分析对方应手
            opponent = Color.WHITE if color == Color.BLACK else Color.BLACK
            analysis = self.analyze(opponent, visits=visits)
            
            # 保存这手棋的信息
            if analysis:
                results[move] = MoveAnalysis(
                    move=move,
                    visits=0,
                    winrate=analysis[0].winrate if analysis else 0.5,
                    score_lead=analysis[0].score_lead if analysis else 0.0,
                    policy=0.0,
                    pv=[]
                )
            else:
                results[move] = MoveAnalysis(
                    move=move,
                    visits=0,
                    winrate=0.5,
                    score_lead=0.0,
                    policy=0.0
                )
            
            # 撤销
            self.undo()
            self.undo()
        
        return results
    
    # ============ SGF 棋谱分析 ============
    
    def analyze_sgf(self, 
                     sgf_path: str,
                     moves_to_analyze: Optional[List[int]] = None,
                     visits: int = 200) -> Dict[int, List[MoveAnalysis]]:
        """
        分析 SGF 棋谱的指定局面
        
        Args:
            sgf_path: SGF 文件路径
            moves_to_analyze: 要分析的手数列表 (如 [50, 100, 150])
            visits: 搜索次数
            
        Returns:
            {手数: 分析结果}
        """
        results = {}
        
        # 加载 SGF
        response = self._send_command(f'loadsgf {sgf_path}')
        if not response.startswith('='):
            print(f"加载 SGF 失败: {response}")
            return results
        
        # 获取棋盘状态
        response = self._send_command('printsgf')
        board_info = self._parse_board_info(response)
        
        if not moves_to_analyze:
            # 分析所有关键点
            total_moves = board_info.get('moves', 0)
            moves_to_analyze = [i for i in range(10, total_moves, 10)]  # 每10手分析
        
        for move_num in moves_to_analyze:
            if move_num > board_info.get('moves', 0):
                break
            
            # 前进到指定局面
            self._send_command(f'gogui-gfx-analyze_commands\n')
            # 这里简化处理，实际应逐手复盘
            
            print(f"\n分析第 {move_num} 手:")
            analysis = self.analyze(Color.WHITE, visits=visits, verbose=True)
            results[move_num] = analysis
        
        return results
    
    def _parse_board_info(self, response: str) -> Dict[str, Any]:
        """解析棋盘信息"""
        info = {}
        lines = response.split('\n')
        for line in lines:
            if 'Moves' in line:
                info['moves'] = int(line.split(':')[1].strip())
        return info
    
    # ============ 上下文管理器 ============
    
    def __enter__(self):
        """进入上下文"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        self.stop()


def demo():
    """演示"""
    print("=" * 60)
    print("KataGo 分析器演示")
    print("=" * 60)
    
    model_path = "/Users/haoc/.katago/models/kata1-b28c512nbt-s12374138624-d5703190512.bin.gz"
    
    with KataGoAnalyzer(model_path) as katago:
        # 设置棋盘
        katago.set_board_size(19)
        katago.set_komi(7.5)
        katago.clear_board()
        
        # 摆一个简单局面
        print("\n摆一个简单局面...")
        katago.play(Color.BLACK, "Q16")  # 星位
        katago.play(Color.WHITE, "D4")  # 挂角
        katago.play(Color.BLACK, "D16")  # 挂角
        katago.play(Color.WHITE, "Q4")  # 挂角
        
        # 分析当前局面
        print("\n分析当前局面 (执白):")
        results = katago.analyze(Color.WHITE, visits=50, verbose=True)
        
        if results:
            best = results[0]
            print(f"\n最佳着法: {best.move}")
            print(f"胜率: {best.winrate*100:.1f}%")
            print(f"目数领先: {best.score_lead:+.1f}")
        
        # 生成最佳着法
        print("\n生成一手棋:")
        move = katago.genmove(Color.BLACK)
        print(f"KataGo 建议: {move}")


if __name__ == "__main__":
    demo()
