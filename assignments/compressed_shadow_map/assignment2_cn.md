# 作业 2：高级阴影技术

本作业基于作业 1 进行扩展。你将实现三种技术来提升阴影质量和性能。

**前置条件：** 作业 1 已完成（阴影贴图生成和 `get_visibility_shadow_map()` 正常工作）。

---

## 任务 1：泊松圆盘 PCF 结合时序滤波

### 目标

使用泊松圆盘采样实现**百分比接近滤波（PCF）**，并结合**时序滤波**生成平滑的软阴影。

### 背景

基础阴影贴图会产生硬边缘和锯齿。PCF 通过在多个偏移位置采样阴影贴图并平均二值结果来软化边缘。

使用**泊松圆盘分布**可以避免规则网格产生的条带伪影。通过每帧为每个像素**随机旋转**采样模式，并随时间累积，用较少的每帧采样数即可收敛到平滑的软阴影。

项目提供了 `LowDiscrepancyDiskPattern`（`low_discrepancy_disk_pattern.py`），它将 R2 准随机圆盘采样存储在 GPU 的 `StructuredBuffer<float2>` 中。

### 需要修改的文件

- `scene.slang` — 在 `get_visibility_shadow_map()` 中添加 PCF 采样逻辑
- `scene.py` — 绑定泊松圆盘缓冲区和 PCF 参数
- `path_tracing_renderer.py` — 创建并传递 `LowDiscrepancyDiskPattern`

### 核心思路

1. 将圆盘采样缓冲区和 `pcf_filter_radius` 传递给着色器
2. 对每个着色点，使用 `RNG` + `frame_index` 选取随机旋转角度，在缩放到阴影贴图纹素空间之前旋转每个圆盘偏移
3. 在旋转后的偏移位置采样并平均多次阴影贴图查询
4. 现有的 `Accumulator` 负责时序平均 — 由于旋转每帧变化，累积结果会自然收敛

### 验证方法

- `filter_radius = 0` 应重现作业 1 的硬阴影
- 关闭累积时，软边缘应呈现噪点
- 开启累积后，阴影应在约 32 帧后收敛为平滑结果

---

## 任务 2：自适应阴影遮罩

### 目标

参考 [Deferred Adaptive Compute Shading](https://github.com/WeakKnight/DeferredAdaptiveComputeShading) 实现**自适应阴影遮罩** Pass，在几何平滑区域通过插值减少阴影计算。

### 背景

全屏 PCF 开销很大。同一表面上的相邻像素通常具有相同的阴影值。自适应方法：

1. 为稀疏的**锚点像素**（如每 4×4 块一个）计算阴影
2. 对其余像素，使用深度和法线检测与已计算邻居的几何相似性
3. 相似则**插值**；不相似则**计算**
4. 以多 Pass 渐进填充的方式组织，在屏幕空间块上进行

输出是单通道**阴影遮罩**纹理（0 = 阴影，1 = 受光）。

### 需要创建/修改的文件

- **创建 `adaptive_shadow_mask.slang`** — 多 Pass 计算着色器
- **创建 `adaptive_shadow_mask.py`** — Python 包装器
- **修改 `path_tracer.slang`** — 为主光线命中输出 G-Buffer（深度 + 法线）
- **修改 `path_tracing_renderer.py`** — 集成新 Pass

### 核心思路

1. **G-Buffer**：从路径追踪器的主光线命中输出线性深度和世界空间法线
2. **相似性检测**：如果两个像素的深度差和法线夹角都在阈值内，则视为"相似"
3. **多 Pass 填充**：设计从稀疏（锚点）开始渐进填充细节的模式 — 仅在几何不一致的地方计算阴影
4. **世界坐标重建**：使用逆视图投影矩阵 + 深度获取世界坐标，用于 `get_visibility_shadow_map()`

### 验证方法

- 将自适应遮罩与全屏暴力计算的遮罩对比 — 应几乎相同
- 可视化已计算（红色）和插值（绿色）像素，确认自适应模式
- 调节阈值：过于激进 → 阴影泄漏；过于保守 → 无加速效果

---

## 任务 3：光线追踪 + 阴影贴图混合阴影

### 目标

实现**混合阴影**技术：近处使用**光线追踪**，远处使用**阴影贴图**。

### 背景

光线追踪阴影精确但开销大。阴影贴图快速但有锯齿。混合方法各取所长：

- **近距离**（到摄像机距离 < 阈值）：通过 `get_visibility()` 光线追踪，获得无伪影的阴影
- **远距离**：使用 `get_visibility_shadow_map()`，此处锯齿不太明显
- **过渡区**：两者之间平滑过渡，避免接缝

### 需要修改的文件

- `scene.slang` — 添加混合可见性函数
- `scene.py` — 传递距离阈值

### 核心思路

1. 在 `Scene` 结构体中添加 `get_visibility_hybrid()`，根据相机距离选择光追或阴影贴图
2. 在过渡区使用 `smoothstep(near, far, dist)` 对两者结果进行插值
3. 将 `sample_directional_light()` 中的可见性调用替换为混合版本
4. 将 `near_distance` 和 `far_distance` 作为可调参数暴露

### 验证方法

- `near = far = 0`：纯阴影贴图 — 应与作业 1 一致
- `near = far = 极大值`：纯光线追踪 — 应与原始效果一致
- 正常混合模式：近处阴影清晰，远处使用阴影贴图，过渡区无缝衔接

---

## 参考资料

- [百分比接近滤波 (GPU Gems)](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows/chapter-11-shadow-map-antialiasing)
- [泊松圆盘采样](https://www.jasondavies.com/poisson-disc/)
- [延迟自适应计算着色](https://github.com/WeakKnight/DeferredAdaptiveComputeShading)
- [混合光线追踪阴影](https://developer.nvidia.com/blog/hybrid-rendering-for-real-time-ray-tracing/)
