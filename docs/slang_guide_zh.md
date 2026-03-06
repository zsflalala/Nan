# Slang 语言文档 - 完整参考指南

来源: https://github.com/shader-slang/slang

## 目录

- [项目概述](#项目概述)
- [简介及为何使用 Slang](#简介及为何使用-slang)
- [快速入门](#快速入门)
- [语言特性](#语言特性)
- [常规特性](#常规特性)
- [接口与泛型](#接口与泛型)
- [自动微分](#自动微分)
- [模块与访问控制](#模块与访问控制)
- [能力系统 (Capabilities System)](#能力系统-capabilities-system)
- [使用 Slang 编译代码](#使用-slang-编译代码)
- [反射 API](#反射-api)
- [编译目标 (Targets)](#编译目标-targets)
- [目标兼容性](#目标兼容性)
- [命令行参考](#命令行参考)
- [从源码编译](#从源码编译)
- [常见问题 (FAQ)](#常见问题-faq)

## 项目概述

Slang 是一种实时着色语言，旨在在保持高性能的同时，提高开发者进行 GPU 编程的效率。它使用现代编程语言特性对 HLSL 进行了扩展，并支持编译到多个目标平台，包括 Direct3D、Vulkan、CUDA、Metal 和 CPU。

主要优势：
- 向后兼容绝大多数现有的 HLSL 代码
- Parameter blocks (参数块) 可以高效使用描述符表
- Interfaces (接口) 和 Generics (泛型) 提供类型安全的着色器特化
- Automatic differentiation (自动微分) 面向机器学习应用
- 模块系统支持更好的代码组织结构
- 全面的反射 API
- 跨平台编译至多个目标平台

## 简介及为何使用 Slang

### 为何使用 Slang？

Slang 系统帮助实时图形开发者编写更干净、更易于维护的 GPU 代码，且不牺牲运行时性能。Slang 采用了现代通用语言中那些精选的特性，扩展了 HLSL 语言，以提高开发者的生产力和代码质量。

使用 Slang 的部分好处包括：
- **向后兼容**：Slang 兼容绝大多数现有的 HLSL 代码
- **参数块 (Parameter blocks)**：允许着色器参数按更新频率进行分组，从而利用 D3D12 的描述符表 (descriptor tables) 和 Vulkan 的描述符集 (descriptor sets)
- **接口与泛型**：为基于预处理器的着色器特化提供了头等 (first-class) 替代方案
- **自动微分**：极大简化了基于学习的技术在着色器中的实现
- **模块系统**：实现真正的分离编译和着色器代码的语义检查
- **多平台支持**：同一个编译器可生成 DX 字节码、DXIL、SPIR-V、HLSL、GLSL、CUDA 等代码
- **健壮的反射 API**：以一致的格式提供着色器参数的绑定、偏移量及布局信息

### 目标与非目标

主要设计目标：
- **性能**：使用 Slang 所带来的好处绝不能以牺牲性能为代价
- **生产力**：语言概念促进在大型代码库中获得更高的开发者生产力
- **可移植性**：支持各种硬件、图形 API 和操作系统
- **易于采用**：兼容现有代码，语法与其他语言相似且让人熟悉
- **可预测性**：代码的运行行为应该符合直觉，且跨平台保持一致
- **有限范围**：Slang 是一种语言、编译器和模块，而不是引擎或框架

## 快速入门

### 安装

开始使用 Slang 的最简单方法是从 GitHub 仓库下载二进制发布版本。解压文件，在 `/bin/windows-x64/release/` 下找到 `slangc.exe`。注意，`slang.dll` 和 `slang-glslang.dll` 必须与它位于同一目录。

如果需要从源码构建，请参阅[从源码编译](#从源码编译)部分。

### 你的第一个 Slang 着色器

创建一个名为 `hello-world.slang` 的文件：

```hlsl
// hello-world.slang
StructuredBuffer<float> buffer0;
StructuredBuffer<float> buffer1;
RWStructuredBuffer<float> result;

[shader("compute")]
[numthreads(1,1,1)]
void computeMain(uint3 threadId : SV_DispatchThreadID)
{
    uint index = threadId.x;
    result[index] = buffer0[index] + buffer1[index];
}
```

编译成 SPIR-V：
```bat
slangc hello-world.slang -target spirv -o hello-world.spv
```

编译成 GLSL：
```bat
slangc hello-world.slang -target glsl -o hello-world.glsl
```

## 语言特性

### Import 声明 (导入)

为了更好的软件模块化，Slang 引入了 `import` 声明：

```hlsl
// foo.slang
float4 someFunc(float4 x) { return x; }

// bar.slang
import foo;
float4 someOtherFunc(float4 y) { return someFunc(y); }
```

关键细节：
- Import 会使用与 `#include` 相同的搜索路径来寻找 `.slang` 文件
- 多次 import 同一个文件只会被解析一次
- 没有自动的命名空间（可能存在命名冲突）
- 使用 `__exported import` 来重新导出 (re-export) 声明
- Import 不等同于 `#include` —— 两者之间不会共享预处理器宏

### 显式参数块 (Explicit Parameter Blocks)

Slang 支持为使用描述符表/集的参数块提供显式语法：

```hlsl
struct ViewParams
{
    float3 cameraPos;
    float4x4 viewProj;
    TextureCube envMap;
}

ParameterBlock<ViewParams> gViewParams;
```

其内的字段将被分配给寄存器/绑定点，支持全部分配到单一的参数块中。

### 接口与泛型 (Interfaces and Generics)

Slang 支持声明 `interface`，用户定义的 `struct` 类型可以实现它：

```hlsl
// 接口定义
struct LightSample { float3 intensity; float3 direction; };

interface ILight
{
    LightSample sample(float3 position);
}

// 实现接口
struct PointLight : ILight
{
    float3 position;
    float3 intensity;
    
    LightSample sample(float3 hitPos) { ... }
}
```

Slang 使用尖括号语法支持泛型声明：

```hlsl
float4 computeDiffuse<L : ILight>(float4 albedo, float3 P, float3 N, L light)
{
    LightSample sample = light.sample(P);
    float nDotL = max(0, dot(N, sample.direction));
    return albedo * nDotL;
}
```

## 自动微分 (Automatic Differentiation)

Slang 通过自动微分为可微编程提供了原生支持。

### 主要特性
- `fwd_diff` 和 `bwd_diff` 运算符用于前向和反向导数传播
- `DifferentialPair<T>` 类型用于随输入一起传递导数
- 面向可微类型的 `IDifferentiable` 和 `IDifferentiablePtrType` 接口
- 通过 `[ForwardDerivative]` 和 `[BackwardDerivative]` 自定义求导函数
- 兼容所有 Slang 特性：控制流、泛型、接口等

### 前向模式 (Forward-Mode) 示例

```hlsl
[Differentiable]
float2 foo(float a, float b) 
{ 
    return float2(a * b * b, a * a);
}

void main()
{
    DifferentialPair<float> dp_a = diffPair(1.0, 1.0);  // 值与导数
    DifferentialPair<float> dp_b = diffPair(2.4, 0.0);
    
    DifferentialPair<float2> dp_output = fwd_diff(foo)(dp_a, dp_b);
}
```

### 反向模式 (Backward-Mode) 示例

```hlsl
[Differentiable]
float2 foo(float a, float b) { ... }

void main()
{
    DifferentialPair<float> dp_a = diffPair(1.0);
    DifferentialPair<float> dp_b = diffPair(2.4);
    
    float2 dL_doutput = float2(1.0, 0.0);  // 输出导数
    
    bwd_diff(foo)(dp_a, dp_b, dL_doutput);
    
    float dL_da = dp_a.d;  // 计算出的输入导数
}
```

## 模块与访问控制

### 定义模块

一个模块包含一个或多个文件，主文件中包含 `module` 声明：

```hlsl
// scene.slang
module scene;
__include "scene-helpers";
```

### 访问控制与可见性

支持三种级别的可见性：
1. `public`：所有地方都可以访问
2. `private`：只能在同一个类型内访问
3. `internal`（默认）：能在整个所属的模块内部访问

## 能力系统 (Capabilities System)

能力系统用于管理跨越多种 GPU、图形 API 和着色器阶段的硬件功能差异。
能力包含目标 (targets)、阶段 (stages)、扩展 (extensions) 和特性 (features)，例如:
- `GLSL_460` - GLSL 460
- `compute` - compute 阶段着色器
- `_sm_6_7` - Shader Model 6.7

使用方式通过 `[require(capability)]` 属性声明以要求相应的能力配置。

## 使用 Slang 编译代码

命令行使用 `slangc`。

```bat
slangc hello-world.slang -target spirv -o hello-world.spv
```

Slang 为不同目标间提供确定性 (deterministic) 的参数绑定。生成的代码内部包含显式的绑定布局，确保产生跨平台行为一致的参数映射。

如果是程序化执行，你可以使用 `slang::createGlobalSession` 以得到对应的 `slang::ISession`，利用 `slang::IModule` 和 `slang::IComponentType` 进行模块的装载和执行程序的组合链接。

## 反射 API

Slang 提供了一套健壮的反射 API 用以方便读取类型以及相关数据的系统分布。
核心反射类：
- `VariableReflection`: 代表变量声明
- `TypeReflection`: 代表类型声明（标量、结构、数组类型等）
- `ParameterLayout`: 描述参数是怎么被映射到特定目标平台的资源的（涉及绑定区间、index 以及 space。
- `EntryPointLayout`: 有关着色器入口输入/输出的数据声明，以及具体的 stage (渲染管线过程) 语义的传递信息。

## 编译目标及兼容性

Slang 能将通用的源码生成输出：
- **Direct3D 11/12** 相关目标的 DXBC，DXIL 数据
- **Vulkan** API 的 SPIR-V 数据及提供针对 Vulkan 规范描述集支持能力的增强属性
- **CUDA** API 支持下直接用来生成包含有原生指针和计算数学工作量的通用计算目标
- **Metal** 格式
- **CPU/C++** Host侧运行 C++ 程序用于代码 Debug 的实现

由于底层目标的硬件限制差异以及特性范围：
并非所有语法结构等均能全平台通用（比图 Half type、Wave Intrinsics / Tensor 的全面实现、Bindless Native Resource 等相关依赖），Slang 编译器会在检测不兼容情况或缺失 Capabilities 特性定义时报错或预生成。

---

*本文档是从英文原文中通过总结翻译而来，并精简了其中大段的代码样例以便整体概览。如需完整代码范例请参照相关 [原指南地址](https://github.com/shader-slang/slang)。*
