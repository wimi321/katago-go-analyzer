#!/usr/bin/env python3
"""
Katago集成模块
"""

import subprocess
import json
import os

KATAGO_BIN = "/opt/homebrew/bin/katago"
MODEL_PATH = "/Users/haoc/.openclaw/workspace/katago_model.bin.gz"
CONFIG_PATH = "/opt/homebrew/share/katago/configs/analysis_example.cfg"


def analyze_sgf(sgf_path):
    """使用KataGo分析SGF"""
    if not os.path.exists(MODEL_PATH):
        return {"error": f"模型不存在: {MODEL_PATH}"}
    
    # 读取SGF
    with open(sgf_path) as f:
        sgf_content = f.read()
    
    # 构建命令
    cmd = [
        KATAGO_BIN, "analysis",
        "-model", MODEL_PATH,
        "-config", CONFIG_PATH,
        "-override-config", "numAnalysisThreads=2,maxVisits=100,verbose=false"
    ]
    
    print(f"🔮 KataGo分析中...")
    
    try:
        # 运行Katago
        result = subprocess.run(
            cmd,
            input=sgf_content,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # 解析输出
            lines = result.stdout.strip().split('\n')
            analysis_data = []
            for line in lines:
                if line.startswith('{'):
                    analysis_data.append(json.loads(line))
            
            return {
                "success": True,
                "moves": analysis_data,
                "summary": parse_analysis(analysis_data)
            }
        else:
            return {"error": result.stderr}
    
    except subprocess.TimeoutExpired:
        return {"error": "分析超时"}
    except Exception as e:
        return {"error": str(e)}


def parse_analysis(analysis_data):
    """解析KataGo分析结果"""
    if not analysis_data:
        return {}
    
    # 取第一手的分析
    first = analysis_data[0] if analysis_data else {}
    moveInfos = first.get("moveInfos", [])
    
    # 获取Top 5推荐
    top_moves = []
    for info in moveInfos[:5]:
        move = info.get("move", "")
        scoreLead = info.get("scoreLead", 0)
        winrate = info.get("winrate", 0)
        points = info.get("points", 0)
        
        # 转换坐标
        if move:
            col = ord(move[0]) - ord('a')
            row = ord(move[1]) - ord('a')
            sgf_move = f"{chr(ord('a') + col)}{chr(ord('a') + row)}"
        else:
            sgf_move = "pass"
        
        top_moves.append({
            "move": sgf_move,
            "winrate": winrate,
            "scoreLead": scoreLead,
            "points": points
        })
    
    # 当前胜率
    turn = first.get("turnNumber", 0)
    current_player = "白" if turn % 2 == 0 else "黑"
    
    return {
        "turn": turn,
        "current_player": current_player,
        "top_moves": top_moves,
        "move_count": len(analysis_data)
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        result = analyze_sgf(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        # 测试
        result = analyze_sgf("/Users/haoc/.openclaw/workspace/test_v3.sgf")
        if "success" in result:
            summary = result["summary"]
            print(f"\n📊 KataGo分析结果:")
            print(f"当前手数: {summary.get('turn', 0)}")
            print(f"当前玩家: {summary.get('current_player', '?')}")
            print(f"\n推荐选点:")
            for i, m in enumerate(summary.get("top_moves", [])[:3]):
                print(f"  {i+1}. {m['move']} - 胜率: {m['winrate']:.1%}, 领先: {m['scoreLead']:.1f}目")
        else:
            print(f"❌ 错误: {result.get('error')}")
