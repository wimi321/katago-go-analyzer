#!/usr/bin/env python3
"""
改进版围棋棋盘识别器 - 修复角点检测问题
主要改进:
1. 鲁棒的角点排序算法
2. 角点质量验证
3. 正确的透视变换和坐标映射
4. 调试可视化
"""

import sys
import os
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

class ImprovedGoBoardRecognizer:
    """改进版围棋棋盘识别器"""
    
    def __init__(self, model_path):
        """加载训练好的模型"""
        self.model = YOLO(model_path)
        self.board_size = 19  # 标准围棋棋盘 19x19
        self.debug = True  # 开启调试模式
    
    def detect(self, image_path):
        """检测棋盘上的角点和棋子"""
        results = self.model(image_path, conf=0.25, iou=0.5)[0]
        
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
    
    def detect_corners_cv(self, image):
        """使用CV方法检测棋盘角点"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 查找最大的四边形轮廓
        max_area = 0
        best_quad = None
        
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                if area > max_area:
                    max_area = area
                    best_quad = approx
        
        if best_quad is None:
            print("⚠️  CV方法未找到四边形轮廓")
            return []
        
        # 转换为标准格式
        corners = []
        for point in best_quad:
            x, y = point[0]
            corners.append({
                'class': 2,
                'conf': 1.0,
                'center': [float(x), float(y)]
            })
        
        print(f"✓ CV方法检测到 {len(corners)} 个角点")
        return corners
    
    def detect_corners_hough(self, image):
        """使用霍夫直线检测棋盘边界"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 霍夫直线检测
        lines = cv2.HoughLinesP(
            edges, 
            rho=1, 
            theta=np.pi/180, 
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )
        
        if lines is None:
            print("⚠️  霍夫方法未检测到直线")
            return []
        
        # 分离水平线和垂直线
        h_lines = []
        v_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            if abs(angle) < 10 or abs(angle - 180) < 10:
                h_lines.append(line[0])
            elif abs(angle - 90) < 10 or abs(angle + 90) < 10:
                v_lines.append(line[0])
        
        if len(h_lines) < 2 or len(v_lines) < 2:
            print(f"⚠️  直线数量不足: 水平{len(h_lines)}, 垂直{len(v_lines)}")
            return []
        
        # 找到最外围的4条线
        h_lines_sorted = sorted(h_lines, key=lambda l: (l[1] + l[3]) / 2)
        v_lines_sorted = sorted(v_lines, key=lambda l: (l[0] + l[2]) / 2)
        
        top_line = h_lines_sorted[0]
        bottom_line = h_lines_sorted[-1]
        left_line = v_lines_sorted[0]
        right_line = v_lines_sorted[-1]
        
        # 计算交点
        corners = []
        line_pairs = [
            (left_line, top_line),    # 左上
            (right_line, top_line),   # 右上
            (right_line, bottom_line), # 右下
            (left_line, bottom_line)   # 左下
        ]
        
        for v_line, h_line in line_pairs:
            intersection = self._line_intersection(v_line, h_line)
            if intersection is not None:
                corners.append({
                    'class': 2,
                    'conf': 1.0,
                    'center': intersection
                })
        
        print(f"✓ 霍夫方法检测到 {len(corners)} 个角点")
        return corners
    
    def _line_intersection(self, line1, line2):
        """计算两条线段的交点"""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-6:
            return None
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        
        return [float(x), float(y)]
    
    def sort_corners_robust(self, corners):
        """鲁棒的角点排序算法 - 返回顺时针: 左上、右上、右下、左下"""
        if len(corners) != 4:
            return corners
        
        pts = np.array([c['center'] for c in corners], dtype=np.float32)
        
        # 方法: 按x+y排序找左上，按x-y排序找右上
        sums = pts[:, 0] + pts[:, 1]
        diffs = pts[:, 0] - pts[:, 1]
        
        top_left_idx = np.argmin(sums)      # x+y最小
        bottom_right_idx = np.argmax(sums)  # x+y最大
        top_right_idx = np.argmax(diffs)    # x-y最大
        bottom_left_idx = np.argmin(diffs)  # x-y最小
        
        ordered_indices = [top_left_idx, top_right_idx, bottom_right_idx, bottom_left_idx]
        
        ordered_corners = []
        for idx in ordered_indices:
            ordered_corners.append(corners[idx])
        
        print(f"✓ 角点排序完成: 左上→右上→右下→左下")
        return ordered_corners
    
    def validate_corners(self, corners, image_shape):
        """验证角点质量"""
        if len(corners) != 4:
            return False, f"角点数量错误: {len(corners)}"
        
        pts = np.array([c['center'] for c in corners], dtype=np.float32)
        
        # 检查1: 四个点应该形成凸四边形
        hull = cv2.convexHull(pts)
        if len(hull) != 4:
            return False, "角点不构成凸四边形"
        
        # 检查2: 四条边长度应该相近
        edges = []
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i+1) % 4]
            edges.append(np.linalg.norm(p1 - p2))
        
        edge_ratio = max(edges) / min(edges)
        if edge_ratio > 2.0:
            return False, f"边长比例过大: {edge_ratio:.2f}"
        
        # 检查3: 面积应该足够大
        area = cv2.contourArea(pts)
        image_area = image_shape[0] * image_shape[1]
        area_ratio = area / image_area
        
        if area_ratio < 0.2:
            return False, f"棋盘面积过小: {area_ratio:.2%}"
        
        print(f"✓ 角点质量验证通过 (边长比:{edge_ratio:.2f}, 面积比:{area_ratio:.2%})")
        return True, "角点质量良好"
    
    def detect_corners_ensemble(self, image):
        """集成多种方法检测角点"""
        print("\n🔍 开始角点检测...")
        
        candidates = []
        
        # 方法1: CV轮廓检测
        try:
            cv_corners = self.detect_corners_cv(image)
            if len(cv_corners) == 4:
                candidates.append(('CV轮廓', cv_corners))
        except Exception as e:
            print(f"⚠️  CV方法失败: {e}")
        
        # 方法2: 霍夫直线
        try:
            hough_corners = self.detect_corners_hough(image)
            if len(hough_corners) == 4:
                candidates.append(('霍夫直线', hough_corners))
        except Exception as e:
            print(f"⚠️  霍夫方法失败: {e}")
        
        # 选择最佳结果
        best_corners = None
        best_score = 0
        best_method = None
        
        for method, corners in candidates:
            valid, msg = self.validate_corners(corners, image.shape)
            if valid:
                # 计算质量分数（基于边长一致性）
                pts = np.array([c['center'] for c in corners])
                edges = []
                for i in range(4):
                    edges.append(np.linalg.norm(pts[i] - pts[(i+1) % 4]))
                
                # 分数 = 1 / 边长标准差（越小越好）
                score = 1.0 / (np.std(edges) + 1e-6)
                
                print(f"  {method}: 分数={score:.2f}")
                
                if score > best_score:
                    best_score = score
                    best_corners = corners
                    best_method = method
        
        if best_corners:
            print(f"✅ 选择方法: {best_method} (分数: {best_score:.2f})")
        else:
            print("❌ 所有方法都失败了")
        
        return best_corners
    
    def perspective_transform(self, image, corners):
        """透视变换: 将梯形棋盘变换为标准正方形"""
        if len(corners) != 4:
            return image, None
        
        # 源点（已排序: 左上、右上、右下、左下）
        src_pts = np.array([c['center'] for c in corners], dtype=np.float32)
        
        # 目标点（标准正方形）
        dst_size = 1024
        dst_pts = np.array([
            [0, 0],
            [dst_size, 0],
            [dst_size, dst_size],
            [0, dst_size]
        ], dtype=np.float32)
        
        # 计算透视变换矩阵
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # 应用变换
        warped = cv2.warpPerspective(image, M, (dst_size, dst_size))
        
        print(f"✓ 透视变换完成: {image.shape[:2]} → {warped.shape[:2]}")
        return warped, M
    
    def map_stones_to_grid(self, stones, M, image_shape):
        """将棋子坐标映射到19x19网格"""
        if M is None:
            print("❌ 没有变换矩阵，无法映射")
            return {}
        
        board_size = 1024
        cell_size = board_size / 18  # 19x19棋盘有18个间隔
        
        grid_stones = {}
        
        for stone in stones:
            if stone['class'] not in [0, 1]:  # 只处理黑白棋子
                continue
            
            # 原始坐标
            cx, cy = stone['center']
            pt = np.array([[[cx, cy]]], dtype=np.float32)
            
            # 透视变换
            transformed = cv2.perspectiveTransform(pt, M)
            tx, ty = transformed[0][0]
            
            # 映射到网格
            col = int(round(tx / cell_size))
            row = int(round(ty / cell_size))
            
            # 边界检查
            if 0 <= col < 19 and 0 <= row < 19:
                color = 'b' if stone['class'] == 0 else 'w'
                grid_stones[(row, col)] = color
        
        print(f"✓ 映射完成: {len(grid_stones)} 个棋子")
        return grid_stones
    
    def visualize_detection(self, image, corners, stones, output_path):
        """可视化检测结果"""
        vis = image.copy()
        
        # 画角点
        if corners:
            for i, corner in enumerate(corners):
                cx, cy = corner['center']
                cv2.circle(vis, (int(cx), int(cy)), 15, (0, 0, 255), -1)
                cv2.putText(vis, f'{i+1}', (int(cx)-5, int(cy)+5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # 画边界
            pts = np.array([c['center'] for c in corners], dtype=np.int32)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 3)
        
        # 画棋子
        for stone in stones:
            if stone['class'] not in [0, 1]:
                continue
            
            cx, cy = stone['center']
            color = (0, 0, 0) if stone['class'] == 0 else (255, 255, 255)
            border_color = (255, 255, 255) if stone['class'] == 0 else (0, 0, 0)
            
            cv2.circle(vis, (int(cx), int(cy)), 8, color, -1)
            cv2.circle(vis, (int(cx), int(cy)), 8, border_color, 2)
        
        cv2.imwrite(output_path, vis)
        print(f"✓ 可视化结果保存: {output_path}")
    
    def generate_sgf(self, stones, game_info=None):
        """生成SGF格式棋谱"""
        if game_info is None:
            game_info = {
                'black_name': 'Black',
                'white_name': 'White',
                'result': 'Unknown',
                'date': '2026-02-11'
            }
        
        # 生成SGF内容
        sgf_content = f"""(;FF[4]CA[UTF-8]SZ[19]
KM[6.5]
PB[{game_info['black_name']}]
PW[{game_info['white_name']}]
DT[{game_info['date']}]
RE[{game_info['result']}]
"""
        
        # 添加棋子（简化处理，不考虑顺序）
        for (row, col), color in sorted(stones.items()):
            sgf_col = chr(ord('a') + col)
            sgf_row = chr(ord('a') + row)
            color_letter = 'B' if color == 'b' else 'W'
            sgf_content += f"{color_letter}[{sgf_col}{sgf_row}]\n"
        
        sgf_content += ")"
        
        return sgf_content
    
    def process_image(self, image_path, output_dir=None):
        """处理单张图片，输出SGF"""
        print(f"\n{'='*60}")
        print(f"📸 处理图片: {image_path}")
        print(f"{'='*60}")
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 无法加载图片: {image_path}")
            return None, None, None
        
        print(f"✓ 图片尺寸: {image.shape[:2]}")
        
        # 1. 检测所有对象（棋子+角点）
        print("\n🎯 检测棋子...")
        detections = self.detect(image_path)
        stones = [d for d in detections if d['class'] in [0, 1]]
        print(f"✓ 检测到 {len(stones)} 个棋子 (黑:{len([s for s in stones if s['class']==0])}, 白:{len([s for s in stones if s['class']==1])})")
        
        # 2. 检测角点（集成多种方法）
        corners = self.detect_corners_ensemble(image)
        
        if not corners or len(corners) != 4:
            print("❌ 角点检测失败")
            return None, None, None
        
        # 3. 排序角点
        sorted_corners = self.sort_corners_robust(corners)
        
        # 4. 透视变换
        print("\n🔄 执行透视变换...")
        warped, M = self.perspective_transform(image, sorted_corners)
        
        # 5. 映射棋子到网格
        print("\n📍 映射棋子坐标...")
        grid_stones = self.map_stones_to_grid(stones, M, image.shape)
        
        # 6. 生成SGF
        print("\n📝 生成SGF棋谱...")
        sgf_content = self.generate_sgf(grid_stones)
        
        # 7. 保存结果
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # 保存可视化
            vis_path = os.path.join(output_dir, f"{base_name}_detection.jpg")
            self.visualize_detection(image, sorted_corners, stones, vis_path)
            
            # 保存变换后的图像
            warped_path = os.path.join(output_dir, f"{base_name}_warped.jpg")
            cv2.imwrite(warped_path, warped)
            print(f"✓ 变换图像保存: {warped_path}")
            
            # 保存SGF
            sgf_path = os.path.join(output_dir, f"{base_name}.sgf")
            with open(sgf_path, 'w', encoding='utf-8') as f:
                f.write(sgf_content)
            print(f"✓ SGF棋谱保存: {sgf_path}")
        
        print(f"\n{'='*60}")
        print(f"✅ 处理完成! 识别到 {len(grid_stones)} 个棋子")
        print(f"{'='*60}\n")
        
        return sgf_content, grid_stones, sorted_corners


if __name__ == "__main__":
    model_path = '/Users/haoc/.openclaw/workspace/runs/detect/runs/go_board_yolo26/exp/weights/best.pt'
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("用法: python3 04_improved_inference.py <image_path>")
        sys.exit(1)
    
    if not os.path.exists(image_path):
        print(f"❌ 图片不存在: {image_path}")
        sys.exit(1)
    
    recognizer = ImprovedGoBoardRecognizer(model_path)
    
    # 输出目录
    output_dir = '/Users/haoc/.openclaw/workspace/go_output'
    
    sgf_content, stones, corners = recognizer.process_image(image_path, output_dir)
    
    if sgf_content:
        print("\n=== SGF 内容 ===")
        print(sgf_content)
