# 如何编写一个渲染 Pass

本文档以 `ShadowMapPass` 为例，介绍如何在 Nan 渲染器中创建一个自定义的渲染 Pass。

---

## 核心概念：Python 与 Slang 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                      Python (.py)                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • 资源管理 (创建纹理、Buffer)                        │    │
│  │  • 计算矩阵、参数                                     │    │
│  │  • 调度 Shader (dispatch)                            │    │
│  │  • 与渲染管线集成                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ 传递参数                         │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Slang (.slang)                    │    │
│  │  • GPU 上的实际计算逻辑                               │    │
│  │  • 光线追踪、像素处理等                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**简单理解**：
- **Python** = 指挥官，负责"准备工作"和"下达命令"
- **Slang** = 士兵，负责"执行具体计算"

---

## 第一步：编写 Slang Shader

### 文件结构

```slang
// shadow_map.slang

import scene;    // 导入场景模块 (包含光追功能)
import common;   // 导入通用定义

// 1. 定义参数结构体
struct ShadowMapGenerator {
    RWTexture2D<float> shadow_map;      // 输出纹理 (可读写)
    float4x4 light_view_matrix;          // 输入参数
    float4x4 inv_light_view_matrix;
    float3 light_direction;
    float ortho_size;
    float near_plane;
    float far_plane;
    
    // 2. 核心执行函数
    void execute(uint2 pixel)
    {
        // 具体的 GPU 计算逻辑
        // ...
    }
}

// 3. Compute Shader 入口点
[shader("compute")]
[numthreads(8, 8, 1)]  // 线程组大小
void compute_main(uint3 dispatch_thread_id: SV_DispatchThreadID)
{
    uint2 pixel = dispatch_thread_id.xy;
    
    // 边界检查
    uint2 dim;
    g_generator.shadow_map.GetDimensions(dim.x, dim.y);
    if (any(pixel >= dim)) return;
    
    // 调用执行函数
    g_generator.execute(pixel);
}

// 4. 全局参数块声明
ParameterBlock<ShadowMapGenerator> g_generator;
```

### 关键点

| 元素 | 说明 |
|------|------|
| `struct XxxGenerator` | 封装所有输入/输出参数 |
| `void execute(uint2 pixel)` | 每个像素的处理逻辑 |
| `[shader("compute")]` | 声明这是 Compute Shader |
| `[numthreads(8, 8, 1)]` | 每个线程组的大小 |
| `ParameterBlock<T>` | 暴露给 Python 的参数块 |

---

## 第二步：编写 Python 包装类

### 文件结构

```python
# shadow_map.py

import slangpy as spy
from scene import Scene

class ShadowMapPass:
    def __init__(self, device: spy.Device, shadow_map_size=2048):
        self.device = device
        self.size = shadow_map_size
        
        # 1. 加载 Shader 程序
        self.program = device.load_program(
            "shadow_map.slang",    # Slang 文件名
            ["compute_main"]       # 入口点名称
        )
        
        # 2. 创建计算管线
        self.pipeline = device.create_compute_pipeline(self.program)
        
        # 3. 创建输出纹理
        self.shadow_map = device.create_texture(
            width=self.size,
            height=self.size,
            format=spy.Format.r32_float,
            usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource,
            label="shadow_map"
        )
    
    def execute(self, command_encoder: spy.CommandEncoder, scene: Scene, sun_direction):
        # 4. 准备参数
        data = self.get_light_view_data(sun_direction)
        
        # 5. 开始 Compute Pass
        with command_encoder.begin_compute_pass() as pass_encoder:
            # 6. 绑定管线
            shader_object = pass_encoder.bind_pipeline(self.pipeline)
            cursor = spy.ShaderCursor(shader_object)
            
            # 7. 设置参数 (对应 Slang 中的 ParameterBlock)
            g = cursor.g_generator
            g.shadow_map = self.shadow_map
            g.light_view_matrix = data["view"]
            g.inv_light_view_matrix = data["inv_view"]
            g.light_direction = data["light_dir"]
            g.ortho_size = data["ortho_size"]
            g.near_plane = data["near"]
            g.far_plane = data["far"]
            
            # 8. 绑定场景 (如果需要光追)
            scene.bind(cursor.g_scene)
            
            # 9. 调度执行
            pass_encoder.dispatch(thread_count=[self.size, self.size, 1])
```

### Python ↔ Slang 参数对应关系

```
Python 代码                              Slang 代码
─────────────────────────────────────────────────────────────
cursor.g_generator                  ←→  ParameterBlock<ShadowMapGenerator> g_generator
cursor.g_generator.shadow_map       ←→  RWTexture2D<float> shadow_map
cursor.g_generator.light_direction  ←→  float3 light_direction
cursor.g_scene                      ←→  ParameterBlock<Scene> g_scene
```

---

## 第三步：集成到渲染管线

在 `path_tracing_renderer.py` 中：

```python
class PathTracingRenderer:
    def initialize(self, device: spy.Device, scene: Scene):
        # ... 其他初始化 ...
        
        # 创建 Pass 实例
        self.shadow_map_pass = ShadowMapPass(device)
    
    def render(self, command_encoder, output, frame, device, scene, render_data):
        # ... 其他渲染 ...
        
        # 执行 Shadow Map Pass
        if use_shadow_map:
            self.shadow_map_pass.execute(
                command_encoder, 
                scene, 
                scene.sun_direction
            )
        
        # ... 后续 Pass 可以使用 scene.shadow_map ...
```

---

## 完整流程图

```
┌──────────────────────────────────────────────────────────────────┐
│                        创建 Pass 的 4 个步骤                       │
└──────────────────────────────────────────────────────────────────┘

Step 1: 编写 Slang Shader
         ↓
         ├── 定义参数结构体 (struct XxxGenerator)
         ├── 实现 execute() 函数
         ├── 编写 compute_main 入口点
         └── 声明 ParameterBlock

Step 2: 编写 Python 包装类
         ↓
         ├── __init__: 加载程序、创建管线、创建资源
         ├── execute: 绑定参数、调度 Shader
         └── 辅助函数: 计算矩阵等 CPU 端逻辑

Step 3: 集成到 Renderer
         ↓
         ├── 在 initialize() 中创建 Pass 实例
         └── 在 render() 中调用 pass.execute()

Step 4: 传递结果给后续 Pass
         ↓
         └── 通过 Scene 或其他方式共享纹理/数据
```

---

## 常用 API 速查

### 创建资源

```python
# 创建纹理
texture = device.create_texture(
    width=1024, height=1024,
    format=spy.Format.rgba32_float,
    usage=spy.TextureUsage.unordered_access | spy.TextureUsage.shader_resource
)

# 创建 Buffer
buffer = device.create_buffer(
    size=1024,
    usage=spy.BufferUsage.shader_resource
)
```

### Slang 类型对应

| Python | Slang |
|--------|-------|
| `spy.float2(x, y)` | `float2` |
| `spy.float3(x, y, z)` | `float3` |
| `spy.float4(x, y, z, w)` | `float4` |
| `spy.float4x4` | `float4x4` |
| `spy.Texture` | `Texture2D<T>` / `RWTexture2D<T>` |

### 常用格式

| 格式 | 用途 |
|------|------|
| `spy.Format.r32_float` | 单通道深度/灰度 |
| `spy.Format.rgba32_float` | HDR 颜色 |
| `spy.Format.rgba8_unorm` | LDR 颜色 |

---

## 实战练习

尝试创建一个简单的 `GrayscalePass`：

1. **Slang**：读取输入纹理，计算灰度值，写入输出纹理
2. **Python**：创建管线，绑定输入/输出纹理，调度执行
3. **集成**：在 ToneMapper 之后执行

```slang
// grayscale.slang
struct GrayscaleGenerator {
    Texture2D<float4> input;
    RWTexture2D<float4> output;
    
    void execute(uint2 pixel) {
        float3 color = input[pixel].rgb;
        float gray = dot(color, float3(0.299, 0.587, 0.114));
        output[pixel] = float4(gray, gray, gray, 1.0);
    }
}
```
