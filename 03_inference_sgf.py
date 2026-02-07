#!/usr/bin/env python3
"""
端到端推理与 SGF 生成脚本
从棋盘图片到 SGF 棋谱的转换
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

class GoBoardRecognizer:
    """围棋棋盘识别器"""
    
    def __init__(self, model_path):
        """加载训练好的模型"""
        self.model = YOLO(model_path)
        self.board_size = 19  # 标准围棋棋盘 19x19
    
    def detect(self, image_path):
        """检测棋盘上的角点和棋子"""
        results = self.model(image_path, conf=0.25, iou=0.5)[0]
        
        # 提取检测结果
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = box.conf[0].cpu().numpy()
            cls = int(box.cls[0].cpu().numpy())
            
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            width, height = x2 - x1, y2 - y1
            
            detections.append({
                'class': cls,
                'conf': conf,
                'bbox': [x1, y1, width, height],
                'center': [cx, cy]
            })
        
        return detections
    
    def filter_corners(self, detections):
        """筛选置信度最高的 4 个 corner 点"""
        corners = [d for d in detections if d['class'] == 2]  # class 2 = corner
        
        if len(corners) < 4:
            print(f"Warning: Found only {len(corners)} corners, need 4")
            return corners[:4] if corners else []
        
        # 按置信度排序，取最高的 4 个
        corners.sort(key=lambda x: x['conf'], reverse=True)
        return corners[:4]
    
    def sort_corners(self, corners):
        """将角点按顺时针排序: 左上、右上、右下、左下"""
        if len(corners) != 4:
            return corners
        
        centers = [c['center'] for c in corners]
        centers = np.array(centers)
        
        # 计算中心点
        center = centers.mean(axis=0)
        
        # 按角度排序
        def angle(p):
            return np.arctan2(p[1] - center[1], p[0] - center[0])
        
        sorted_indices = np.argsort([angle(p) for p in centers])
        sorted_corners = [corners[i] for i in sorted_indices]
        
        # 调整顺序为: 左上 -> 右上 -> 右下 -> 左下 (顺时针)
        # 根据实际检测结果可能需要调整
        return sorted_corners
    
    def perspective_transform(self, image, corners):
        """透视变换: 将梯形棋盘变换为标准正方形"""
        if len(corners) != 4:
            return image
        
        corners = np.array([c['center'] for c in corners], dtype=np.float32)
        
        # 目标点 (标准正方形)
        dst_size = 1024  # 输出图像大小
        dst_points = np.array([
            [0, 0],
            [dst_size, 0],
            [dst_size, dst_size],
            [0, dst_size]
        ], dtype=np.float32)
        
        # 计算透视变换矩阵
        M = cv2.getPerspectiveTransform(corners, dst_points)
        
        # 应用变换
        warped = cv2.warpPerspective(image, M, (dst_size, dst_size))
        
        return warped, M
    
    def map_to_grid(self, warped, M=None):
        """将棋子坐标映射到 19x19 网格"""
        stones = []
        
        if M is not None:
            # 使用逆变换将检测框中心映射到标准坐标
            # 这里简化处理，实际需要根据变换矩阵调整
            pass
        
        return stones
    
    def extract_board_from_detections(self, detections, original_size, transform_matrix=None):
        """从检测结果中提取棋盘状态"""
        stones = defaultdict(list)  # {(row, col): color}
        
        # 分离黑白棋子
        black_stones = [d for d in detections if d['class'] == 0]
        white_stones = [d for d in detections if d['class'] == 1]
        
        # 计算棋盘格子的实际大小
        # 需要根据角点计算
        if transform_matrix is not None and len(detections) >= 4:
            corners = [d for d in detections if d['class'] == 2]
            if len(corners) >= 4:
                corners = self.sort_corners(corners)
                corner_points = np.array([c['center'] for c in corners], dtype=np.float32)
                
                # 计算棋盘边长
                left_edge = np.linalg.norm(corner_points[0] - corner_points[3])
                right_edge = np.linalg.norm(corner_points[1] - corner_points[2])
                top_edge = np.linalg.norm(corner_points[0] - corner_points[1])
                bottom_edge = np.linalg.norm(corner_points[3] - corner_points[2])
                
                avg_width = (left_edge + right_edge) / 2
                avg_height = (top_edge + bottom_edge) / 2
                
                cell_size = max(avg_width, avg_height) / 18  # 19x19 棋盘有 18 个格子间距
                
                # 计算棋盘区域
                board_min_x = min(c['center'][0] for c in corners)
                board_max_x = max(c['center'][0] for c in corners)
                board_min_y = min(c['center'][1] for c in corners)
                board_max_y = max(c['center'][1] for c in corners)
                
                # 将棋子映射到网格
                for stone in black_stones:
                    cx, cy = stone['center']
                    if board_min_x < cx < board_max_x and board_min_y < cy < board_max_y:
                        col = int((cx - board_min_x) / cell_size)
                        row = int((cy - board_min_y) / cell_size)
                        row = self.board_size - 1 - row  # 翻转 Y 轴
                        stones[(row, col)].append('b')
                
                for stone in white_stones:
                    cx, cy = stone['center']
                    if board_min_x < cx < board_max_x and board_min_y < cy < board_max_y:
                        col = int((cx - board_min_x) / cell_size)
                        row = int((cy - board_min_y) / cell_size)
                        row = self.board_size - 1 - row
                        stones[(row, col)].append('w')
        
        return stones
    
    def generate_sgf(self, stones, game_info=None):
        """生成 SGF 格式棋谱"""
        if game_info is None:
            game_info = {
                'black_name': 'Black',
                'white_name': 'White',
                'result': 'Unknown',
                'date': '2026-02-06'
            }
        
        # 按落子顺序排列 (这里简化处理，实际需要根据时间或其他特征排序)
        moves = []
        positions = set()
        
        for (row, col), color_list in sorted(stones.items()):
            for color in color_list:
                if (row, col) not in positions:
                    positions.add((row, col))
                    # SGF 坐标: aa, ab, ac... (a=0, b=1, ...)
                    sgf_col = chr(ord('a') + col)
                    sgf_row = chr(ord('a') + row)
                    moves.append((color, f"{sgf_col}{sgf_row}"))
        
        # 生成 SGF 内容
        sgf_content = """(;FF[4]CA[UTF-8]SZ[19]
KM[6.5]
PB[{black}]
PW[{white}]
BR[{black_rank}]
WR[{white_rank}]
DT[{date}]
RE[{result}]
""".format(
            black=game_info['black_name'],
            white=game_info['white_name'],
            black_rank='',
            white_rank='',
            date=game_info['date'],
            result=game_info['result']
        )
        
        # 添加每一手
        for i, (color, move) in enumerate(moves):
            color_letter = 'B' if color == 'b' else 'W'
            sgf_content += f"{color_letter}[{move}]\n"
        
        sgf_content += ")"
        
        return sgf_content
    
    def process_image(self, image_path, output_sgf_path=None):
        """处理单张图片，输出 SGF"""
        print(f"Processing: {image_path}")
        
        # 1. 检测
        detections = self.detect(image_path)
        print(f"Detected {len(detections)} objects")
        
        # 2. 筛选角点
        corners = self.filter_corners(detections)
        print(f"Found {len(corners)} corners")
        
        # 3. 排序角点
        sorted_corners = self.sort_corners(corners)
        print(f"Sorted corners: {[c['conf'] for c in sorted_corners]}")
        
        # 4. 透视变换
        image = cv2.imread(image_path)
        if sorted_corners and len(sorted_corners) == 4:
            warped, M = self.perspective_transform(image, sorted_corners)
            # 保存变换后的图像用于调试
            cv2.imwrite(image_path.replace('.jpg', '_warped.jpg'), warped)
        else:
            M = None
        
        # 5. 提取棋盘状态
        stones = self.extract_board_from_detections(detections, image.shape[:2], M)
        print(f"Found {len(stones)} stones")
        
        # 6. 生成 SGF
        sgf_content = self.generate_sgf(stones)
        
        if output_sgf_path:
            with open(output_sgf_path, 'w', encoding='utf-8') as f:
                f.write(sgf_content)
            print(f"SGF saved to: {output_sgf_path}")
        
        return sgf_content, stones, sorted_corners


def batch_process(image_dir, model_path, output_dir):
    """批量处理图片"""
    os.makedirs(output_dir, exist_ok=True)
    recognizer = GoBoardRecognizer(model_path)
    
    for filename in os.listdir(image_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_dir, filename)
            sgf_path = os.path.join(output_dir, filename.rsplit('.', 1)[0] + '.sgf')
            
            try:
                sgf, stones, corners = recognizer.process_image(image_path, sgf_path)
                print(f"Processed: {filename} -> {len(stones)} stones")
            except Exception as e:
                print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    # 单张图片测试
    model_path = '/Users/haoc/.openclaw/workspace/runs/go_board_detection/weights/best.pt'
    image_path = '/Users/haoc/.openclaw/workspace/test_board.jpg'
    
    recognizer = GoBoardRecognizer(model_path)
    
    if os.path.exists(image_path):
        sgf_content, stones, corners = recognizer.process_image(image_path)
        print("\n=== SGF Content ===")
        print(sgf_content)
    else:
        print("Test image not found. Please provide a test image path.")
    
    # 或者批量处理
    # batch_process(
    #     image_dir='/Users/haoc/.openclaw/workspace/test_images',
    #     model_path=model_path,
    #     output_dir='/Users/haoc/.openclaw/workspace/output_sgf'
    # )
