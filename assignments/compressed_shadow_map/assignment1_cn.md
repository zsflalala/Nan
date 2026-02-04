# 作业 1：色调映射曝光控制 & 阴影映射

本作业包含两个任务，帮助您熟悉 Nan 渲染器的基本结构和渲染管线。

---

## 任务 1：Tone Mapper 曝光控制

### 目标

为 Tone Mapper 添加**曝光 (exposure)** 参数，允许用户调整图像亮度。

### 背景知识

曝光控制是后处理管线中最基础的操作之一。在色调映射之前，我们通过曝光因子来缩放 HDR 颜色值：

```
exposed_color = color * pow(2, exposure)
```

其中 `exposure` 单位为 **EV (曝光值)**：
- `exposure = 0`：无变化
- `exposure = 1`：亮度翻倍
- `exposure = -1`：亮度减半

### 需要修改的文件

1. **`tone_mapper.slang`** - Shader 代码
2. **`tone_mapper.py`** - Python 包装器

### 分步指南

#### 步骤 1：修改 Slang Shader

在 `tone_mapper.slang` 中：

1. 向 `ToneMapper` 结构体添加 `exposure` 参数
2. 在 `execute()` 函数中调用 `aces_film()` 之前应用曝光：

```slang
struct ToneMapper {
    Texture2D<float4> input;
    RWTexture2D<float4> output;
    float exposure;  // 添加此行

    void execute(uint2 pixel)
    {
        float3 i = input[pixel].xyz;
        // TODO: 在此处应用曝光
        float3 o = aces_film(i);
        output[pixel] = float4(o, 1.0);
    }
}
```

#### 步骤 2：修改 Python 包装器

在 `tone_mapper.py` 中：

1. 添加 `exposure` 成员变量（默认值 0.0）
2. 修改 `execute()` 方法，将 `exposure` 传递给 shader

```python
class ToneMapper:
    def __init__(self, device: spy.Device):
        # ...
        self.exposure = 0.0  # 添加此行

    def execute(self, command_encoder, input, output):
        self.kernel.dispatch(
            # ...
            vars={
                "g_tone_mapper": {
                    "input": input,
                    "output": output,
                    "exposure": self.exposure,  # 添加此行
                }
            },
            # ...
        )
```

### 验证

修改 `self.exposure` 的值并观察渲染结果：
- 设置为 `2.0`：图像应变得明显更亮
- 设置为 `-2.0`：图像应变得明显更暗

### 加分项（可选）

在 `path_tracing_renderer.py` 中添加 UI 控件，使用滑动条实时调整曝光。

---

## 任务 2：方向光阴影映射

### 目标

使用 **Shadow Map（阴影贴图）** 替换当前的光线追踪可见性测试，以计算方向光的阴影。

### 背景知识

Shadow Mapping 是一种经典的实时阴影技术：

1. **第一遍**：从光源视角渲染场景，将深度值存储到阴影贴图中
2. **第二遍**：渲染场景时，将每个像素转换到光源空间，并与阴影贴图中的深度进行比较，判断是否处于阴影中

对于方向光，我们使用**正交投影**来生成阴影贴图。

### 重要说明：基于光线追踪的阴影贴图生成

**在本作业中，我们不使用任何光栅化。** 阴影贴图使用**带正交投影的光线追踪**生成：

- 从与光线方向对齐的虚拟正交相机发射光线
- 对于阴影贴图中的每个像素，追踪一条光线并记录命中距离作为深度
- 这种方法与 Nan 的全光线追踪架构保持一致

这与使用光栅化的传统阴影映射不同。在这里，我们对所有内容都使用光线追踪，包括阴影贴图的生成。

### 当前实现

在 `scene.slang` 的 `sample_directional_light()` 函数中，可见性当前使用光线追踪计算：

```slang
// 当前实现（第 392-394 行）
Ray shadow_ray = Ray(sd.compute_new_ray_origin(), L_dir);
float visibility = get_visibility(shadow_ray);
```

### 需要创建/修改的文件

1. **创建 `shadow_map.slang`** - 阴影贴图生成计算着色器
2. **创建 `shadow_map.py`** - 阴影贴图生成 Pass
3. **修改 `scene.slang`** - 添加阴影贴图采样逻辑
4. **修改 `scene.py`** - 传递阴影贴图数据
5. **修改 `path_tracing_renderer.py`** - 集成阴影贴图 Pass

### 分步指南

#### 步骤 1：创建阴影贴图生成 Pass

创建 `shadow_map.slang`：

```slang
// 使用带正交投影的光线追踪生成阴影贴图
// 
// 核心概念：不使用光栅化，而是从正交相机追踪光线来计算深度值。
//
// 对于阴影贴图中的每个纹素 (x, y)：
// 1. 使用正交投影计算光线起点（无透视除法）
// 2. 光线方向 = 光照方向（所有光线平行）
// 3. 追踪光线并存储深度

import scene;

struct ShadowMapGenerator {
    RWTexture2D<float> shadow_map;
    float4x4 light_view_matrix;
    float3 light_direction;
    float ortho_size;        // 正交视锥体的半尺寸
    float near_plane;
    float far_plane;
    
    void execute(uint2 pixel)
    {
        uint2 dim;
        shadow_map.GetDimensions(dim.x, dim.y);
        
        // 将像素转换为归一化坐标 [-1, 1]
        float2 ndc = (float2(pixel) + 0.5) / float2(dim) * 2.0 - 1.0;
        
        // 正交光线起点（无透视除法）
        // TODO: 计算世界空间中的光线起点
        
        // 所有光线指向同一方向（平行投影）
        float3 ray_dir = light_direction;
        
        // TODO: 追踪光线并存储深度
    }
}
```

创建 `shadow_map.py`：

```python
class ShadowMapPass:
    def __init__(self, device, shadow_map_size=2048):
        # 创建阴影贴图纹理（R32_FLOAT 格式存储深度）
        # 加载计算着色器
        pass
    
    def execute(self, command_encoder, scene, light_direction):
        # 计算光源视图矩阵和正交边界
        # 调度计算着色器追踪光线并填充阴影贴图
        pass
```

#### 步骤 2：修改 Scene 以使用阴影贴图

在 `scene.slang` 的 `Scene` 结构体中添加：

```slang
struct Scene {
    // ... 现有成员 ...
    
    Texture2D<float> shadow_map;          // 添加此行
    float4x4 light_view_proj_matrix;      // 添加此行
    float shadow_map_size;                // 添加此行
    
    // 新函数：使用阴影贴图计算可见性
    float get_visibility_shadow_map(float3 world_pos)
    {
        // TODO: 
        // 1. 将 world_pos 转换到光源裁剪空间
        // 2. 转换为阴影贴图 UV 坐标
        // 3. 采样阴影贴图深度
        // 4. 比较深度以确定可见性
        // 5. 可选：添加偏差以防止阴影失真
    }
}
```

#### 步骤 3：替换可见性测试

在 `sample_directional_light()` 中，将：

```slang
Ray shadow_ray = Ray(sd.compute_new_ray_origin(), L_dir);
float visibility = get_visibility(shadow_ray);
```

替换为：

```slang
float visibility = get_visibility_shadow_map(sd.position);
```

### 验证

1. 运行渲染器并检查阴影是否正确显示
2. 比较光线追踪可见性和阴影贴图之间的结果
3. 查找阴影失真 (shadow acne) 或悬浮 (peter panning) 伪影

### 实现注意事项

1. **光源空间矩阵**：
   - 视图矩阵：从光照方向朝向场景中心观察
   - 投影矩阵：覆盖整个场景的正交投影

2. **阴影偏差**：
   - 添加深度偏差以防止阴影失真
   - 常见方法：恒定偏差 `depth += bias` 或斜率缩放偏差

3. **PCF (Percentage Closer Filtering)** (可选加分)：
   - 多次采样阴影贴图并平均结果
   - 产生柔和的阴影边缘

### 加分项（可选）

1. 实现 PCF 软阴影

---

## 参考资料

- [Learn OpenGL - Shadow Mapping](https://learnopengl.com/Advanced-Lighting/Shadows/Shadow-Mapping)
- [Percentage-Closer Filtering](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows/chapter-11-shadow-map-antialiasing)
