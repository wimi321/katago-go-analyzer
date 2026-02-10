# 围棋棋盘识别问题诊断与解决方案

## 问题描述

**现状**:
- ✅ 棋子识别很快，坐标准确
- ❌ 棋盘识别不好，导致坐标对应不上
- ❌ 识别不精确

**核心问题**: 棋盘四角点检测不准确，导致透视变换失败

---

## 当前实现分析

### 文件: `03_inference_sgf.py`

#### 当前流程
```
1. YOLO检测棋子（黑、白、角点）
2. filter_corners() 使用CV方法检测角点
3. sort_corners() 排序角点
4. perspective_transform() 透视变换
5. extract_board_from_detections() 映射到19x19网格
6. generate_sgf() 生成SGF棋谱
```

#### 问题定位

**1. 角点检测方法混乱**
```python
# 当前有两种方法:
# 方法1: YOLO检测角点（class=2）
# 方法2: CV传统方法（Canny边缘 + 轮廓检测）

# 问题: 两种方法结果不一致，且都不够准确
```

**2. 透视变换逻辑问题**
```python
def perspective_transform(self, image, corners):
    # 假设corners已经是顺时针排序: 左上、右上、右下、左下
    # 但实际排序逻辑有bug
    
    # 目标点固定为1024x1024正方形
    dst_points = np.array([
        [0, 0],           # 左上
        [dst_size, 0],    # 右上
        [dst_size, dst_size],  # 右下
        [0, dst_size]     # 左下
    ])
```

**3. 坐标映射不准确**
```python
def extract_board_from_detections(...):
    # 当前使用简单的线性映射
    col = int(round((cx - board_min_x) / cell_size))
    row = int(round((cy - board_min_y) / cell_size))
    
    # 问题: 没有考虑透视变换后的坐标系
    # 应该先将原始坐标变换到标准坐标系，再映射
```

---

## 解决方案

### 方案1: 改进角点检测（推荐）

#### 1.1 使用霍夫直线检测
```python
def detect_board_lines(self, image):
    """检测棋盘的直线，找到交点作为角点"""
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
    
    # 分离水平线和垂直线
    h_lines = []  # 水平线
    v_lines = []  # 垂直线
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        
        if abs(angle) < 10 or abs(angle - 180) < 10:
            h_lines.append(line)
        elif abs(angle - 90) < 10 or abs(angle + 90) < 10:
            v_lines.append(line)
    
    # 找到最外围的4条线（上下左右）
    # 计算交点得到4个角点
    corners = self._find_line_intersections(h_lines, v_lines)
    
    return corners
```

#### 1.2 使用棋盘格检测
```python
def detect_chessboard_corners(self, image):
    """使用OpenCV的棋盘格检测"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 尝试检测19x19的棋盘格
    ret, corners = cv2.findChessboardCorners(
        gray, 
        (18, 18),  # 19x19棋盘有18x18个内角点
        flags=cv2.CALIB_CB_ADAPTIVE_THRESH + 
              cv2.CALIB_CB_NORMALIZE_IMAGE
    )
    
    if ret:
        # 提取四个外角点
        outer_corners = [
            corners[0],           # 左上
            corners[17],          # 右上
            corners[-1],          # 右下
            corners[-18]          # 左下
        ]
        return outer_corners
    
    return None
```

### 方案2: 改进透视变换

#### 2.1 正确的角点排序
```python
def sort_corners_robust(self, corners):
    """鲁棒的角点排序算法"""
    if len(corners) != 4:
        return corners
    
    # 转换为numpy数组
    pts = np.array([c['center'] for c in corners], dtype=np.float32)
    
    # 计算质心
    center = pts.mean(axis=0)
    
    # 按到质心的角度排序
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    sorted_indices = np.argsort(angles)
    
    # 找到左上角（角度最小的点）
    # 然后按顺时针排列
    sorted_pts = pts[sorted_indices]
    
    # 确定哪个是左上角（x+y最小）
    sums = sorted_pts[:, 0] + sorted_pts[:, 1]
    top_left_idx = np.argmin(sums)
    
    # 重新排列为: 左上、右上、右下、左下
    ordered_pts = np.roll(sorted_pts, -top_left_idx, axis=0)
    
    # 转换回原始格式
    ordered_corners = []
    for pt in ordered_pts:
        ordered_corners.append({
            'class': 2,
            'conf': 1.0,
            'center': pt.tolist()
        })
    
    return ordered_corners
```

#### 2.2 改进坐标映射
```python
def map_stones_to_grid(self, stones, corners, image_shape):
    """将棋子坐标映射到19x19网格"""
    if len(corners) != 4:
        return {}
    
    # 获取角点坐标
    src_pts = np.array([c['center'] for c in corners], dtype=np.float32)
    
    # 定义标准棋盘坐标（19x19）
    board_size = 1024
    cell_size = board_size / 18  # 18个间隔
    
    dst_pts = np.array([
        [0, 0],
        [board_size, 0],
        [board_size, board_size],
        [0, board_size]
    ], dtype=np.float32)
    
    # 计算透视变换矩阵
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # 映射每个棋子
    grid_stones = {}
    
    for stone in stones:
        # 原始坐标
        cx, cy = stone['center']
        pt = np.array([[cx, cy]], dtype=np.float32)
        
        # 透视变换
        transformed = cv2.perspectiveTransform(pt.reshape(1, 1, 2), M)
        tx, ty = transformed[0][0]
        
        # 映射到网格
        col = int(round(tx / cell_size))
        row = int(round(ty / cell_size))
        
        # 边界检查
        if 0 <= col < 19 and 0 <= row < 19:
            color = 'b' if stone['class'] == 0 else 'w'
            grid_stones[(row, col)] = color
    
    return grid_stones
```

### 方案3: 使用深度学习检测角点（最佳）

#### 3.1 训练专门的角点检测模型
```python
# 数据标注: 只标注棋盘的4个外角点
# 使用更大的模型（YOLOv8m或YOLOv8l）
# 增加角点样本的权重

# 训练命令
model = YOLO('yolov8m.pt')
model.train(
    data='go_board_corners.yaml',
    epochs=100,
    imgsz=1024,
    batch=8,
    patience=20,
    # 角点检测专用配置
    conf=0.5,
    iou=0.3
)
```

#### 3.2 两阶段检测
```python
class TwoStageRecognizer:
    """两阶段识别器"""
    
    def __init__(self, corner_model_path, stone_model_path):
        self.corner_model = YOLO(corner_model_path)  # 专门检测角点
        self.stone_model = YOLO(stone_model_path)    # 检测棋子
    
    def process(self, image_path):
        # 阶段1: 检测角点
        corners = self.corner_model(image_path, conf=0.5)[0]
        
        # 阶段2: 透视变换
        warped, M = self.perspective_transform(image, corners)
        
        # 阶段3: 在变换后的图像上检测棋子
        stones = self.stone_model(warped, conf=0.25)[0]
        
        # 阶段4: 映射到网格（此时坐标已经是标准的）
        grid = self.map_to_grid(stones, warped.shape)
        
        return grid
```

---

## 立即可行的改进

### 改进1: 增加调试可视化
```python
def visualize_detection(self, image, corners, stones):
    """可视化检测结果"""
    vis = image.copy()
    
    # 画角点
    for corner in corners:
        cx, cy = corner['center']
        cv2.circle(vis, (int(cx), int(cy)), 10, (0, 0, 255), -1)
        cv2.putText(vis, 'Corner', (int(cx), int(cy)-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # 画棋子
    for stone in stones:
        cx, cy = stone['center']
        color = (0, 0, 0) if stone['class'] == 0 else (255, 255, 255)
        cv2.circle(vis, (int(cx), int(cy)), 5, color, -1)
    
    # 画连线（显示棋盘边界）
    if len(corners) == 4:
        pts = np.array([c['center'] for c in corners], dtype=np.int32)
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
    
    return vis
```

### 改进2: 添加质量检查
```python
def validate_corners(self, corners):
    """验证角点质量"""
    if len(corners) != 4:
        return False, "角点数量不是4个"
    
    pts = np.array([c['center'] for c in corners])
    
    # 检查1: 四个点应该形成凸四边形
    hull = cv2.convexHull(pts.astype(np.float32))
    if len(hull) != 4:
        return False, "角点不构成凸四边形"
    
    # 检查2: 四条边长度应该相近（正方形棋盘）
    edges = []
    for i in range(4):
        p1 = pts[i]
        p2 = pts[(i+1) % 4]
        edges.append(np.linalg.norm(p1 - p2))
    
    edge_ratio = max(edges) / min(edges)
    if edge_ratio > 1.5:
        return False, f"边长比例过大: {edge_ratio:.2f}"
    
    # 检查3: 面积应该足够大（占图像的一定比例）
    area = cv2.contourArea(pts.astype(np.float32))
    # 假设图像大小已知
    # min_area = image_area * 0.3  # 至少占30%
    
    return True, "角点质量良好"
```

### 改进3: 多方法融合
```python
def detect_corners_ensemble(self, image):
    """集成多种方法检测角点"""
    candidates = []
    
    # 方法1: YOLO检测
    yolo_corners = self.detect_yolo(image)
    candidates.append(('yolo', yolo_corners))
    
    # 方法2: 轮廓检测
    contour_corners = self.filter_corners(image)
    candidates.append(('contour', contour_corners))
    
    # 方法3: 霍夫直线
    hough_corners = self.detect_board_lines(image)
    candidates.append(('hough', hough_corners))
    
    # 选择最佳结果
    best_corners = None
    best_score = 0
    
    for method, corners in candidates:
        if len(corners) == 4:
            valid, msg = self.validate_corners(corners)
            if valid:
                # 计算质量分数
                score = self.calculate_corner_quality(corners)
                if score > best_score:
                    best_score = score
                    best_corners = corners
                    print(f"选择方法: {method}, 分数: {score:.2f}")
    
    return best_corners
```

---

## 测试方案

### 测试数据准备
```bash
# 创建测试集
mkdir -p test_images/easy    # 光线好、角度正
mkdir -p test_images/medium  # 有一定角度
mkdir -p test_images/hard    # 光线差、角度大

# 每个难度准备10张图片
```

### 评估指标
```python
def evaluate_accuracy(predicted_sgf, ground_truth_sgf):
    """评估识别准确率"""
    pred_stones = parse_sgf(predicted_sgf)
    true_stones = parse_sgf(ground_truth_sgf)
    
    # 计算准确率
    correct = 0
    total = len(true_stones)
    
    for pos, color in true_stones.items():
        if pos in pred_stones and pred_stones[pos] == color:
            correct += 1
    
    accuracy = correct / total if total > 0 else 0
    
    # 计算误差分布
    errors = []
    for pos in true_stones:
        if pos not in pred_stones:
            errors.append(('missing', pos))
        elif pred_stones[pos] != true_stones[pos]:
            errors.append(('wrong_color', pos))
    
    return {
        'accuracy': accuracy,
        'correct': correct,
        'total': total,
        'errors': errors
    }
```

---

## 实施计划

### 第一步: 诊断当前问题（今天）
```bash
# 1. 运行现有代码，保存中间结果
python3 03_inference_sgf.py test_image.jpg

# 2. 检查生成的文件
# - test_image_warped.jpg (透视变换后的图像)
# - test_image.sgf (生成的棋谱)

# 3. 可视化检测结果
# 添加 visualize_detection() 并保存图片
```

### 第二步: 实施改进（明天）
1. 实现 `sort_corners_robust()`
2. 实现 `validate_corners()`
3. 实现 `map_stones_to_grid()` 改进版
4. 添加调试可视化

### 第三步: 测试验证（后天）
1. 准备测试数据集
2. 运行评估脚本
3. 分析错误案例
4. 迭代优化

---

## 预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 角点检测成功率 | ~60% | >95% |
| 棋子坐标准确率 | ~70% | >98% |
| 整体SGF准确率 | ~50% | >90% |

---

*创建时间: 2026-02-11 00:56*
