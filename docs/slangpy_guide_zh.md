# SlangPy 文档

> SlangPy 是一个用于在 Slang 着色语言中编写 GPU 计算内核的 Python 库。它允许你使用 Slang 的语法编写计算着色器，并从 Python 中执行它们，支持 NumPy 数组、PyTorch 张量、自动微分，以及高级特性如广播（broadcasting）和类型方法（type methods）。

## 快速入门

### 安装

SlangPy 提供预编译的 wheel 格式包，可通过 PyPi 获取。安装 SlangPy 非常简单，只需运行：

```bash
pip install slangpy
```

要启用 PyTorch 集成，只需像往常一样 `pip install pytorch`，SlangPy 会自动检测到它。

你也可以从源码编译 SlangPy：

```bash
git clone https://github.com/shader-slang/slangpy.git --recursive
cd slangpy
pip install -r requirements-dev.txt
pip install .
```

关于如何从源码编译的更多详细信息，请参阅开发者指南。

## 基础教程

### 你的第一个函数

在这个示例中，我们将初始化 SlangPy，创建一个简单的 Slang 函数，并从 Python 中调用它。

首先，让我们定义一个简单的 Slang 函数，将两个数字相加：

```slang
// example.slang

// 一个将两个数字相加的简单函数
float add(float a, float b)
{
    return a + b;
}
```

接下来，我们创建一个 Python 脚本来初始化 SlangPy，加载 Slang 模块并调用该函数：

```python
## main_scalar.py

import slangpy as spy
import pathlib

# 创建一个 SlangPy 设备；它将在本地文件夹中查找任何 Slang 头文件包含(includes)
device = spy.create_device(include_paths=[
        pathlib.Path(__file__).parent.absolute(),
])

# 加载模块
module = spy.Module.load_from_file(device, "example.slang")

# 调用函数并打印结果
result = module.add(1.0, 2.0)
print(result)

# SlangPy 也支持命名参数
result = module.add(a=1.0, b=2.0)
print(result)
```

在底层，第一次调用这个函数时，SlangPy 会生成一个计算内核（并将其缓存在一个临时文件夹中）。该内核负责从缓冲区加载标量输入，调用 `add` 函数，并将标量结果写回到缓冲区。

虽然这是一个有趣的演示，但仅仅为了将两个数字相加而调度一个计算内核并没有什么效率！不过，既然我们已经建立了一个能运行的环境，我们可以将其规模扩大，直接使用数组来调用该函数：

```python
## main_numpy.py

# ... 此处为初始化代码 ...

# 创建几个包含 1,000,000 个随机浮点数的缓冲区
a = np.random.rand(1000000).astype(np.float32)
b = np.random.rand(1000000).astype(np.float32)

# 调用我们的函数并请求以 numpy 数组形式返回结果（默认是一个缓冲区）
result = module.add(a, b, _result='numpy')

# 打印前 10 个结果
print(result[:10])
```

SlangPy 支持广泛的数据类型，并且能够处理具有任意维度的数组。本示例展示了如何可以传入标量以及 NumPy 数组来调用同一个 Slang 函数。除此之外，SlangPy 还支持更多类型，如缓冲区（buffers）、纹理（textures）和张量（tensors）。

### 返回类型

Slangpy 可以生成不同类型的容器来保存 Slang 函数的返回结果。这样能够方便地以首选容器类型获取结果，如 numpy 数组、纹理或张量。

`_result` 可以是 `'numpy'`、`'texture'` 或 `'tensor'`。你也可以使用 `_result` 直接指定类型，例如 `numpy.ndarray`、`slangpy.Texture` 或 `slangpy.Tensor`。或者，你可以直接传入一个属于这些类型的现有变量来复用它。

使用纹理作为返回类型的示例：

```python
# 创建几个 128x128 随机浮点数的缓冲区
a = np.random.rand(128, 128).astype(np.float32)
b = np.random.rand(128, 128).astype(np.float32)

# 调用我们的函数并请求返回一个纹理
result = module.add(a, b, _result='texture')

# 打印前 5x5 的值
print(result.to_numpy()[:5, :5])

# 使用 tev 显示结果
spy.tev.show(result, name='add random')
```

### 缓冲区 (Buffers)

SlangPy 围绕经典的结构化缓冲区（structured buffers）提供了两个关键的封装类型：`NDBuffer` 和 `Tensor`。

`NDBuffer` 类型接受一个已定义步长和大小的结构化缓冲区，并为其添加：
- **数据类型 (Data type)**: 一个 `SlangType`，它可以是原生类型（例如，float、vector）或用户定义的 Slang 结构体 (struct)。
- **形状 (Shape)**: 一个描述各维度大小的整数元组，类似于 NumPy 数组或 Torch 张量的 shape。

使用自定义 Slang 类型的示例：

```slang
// 目前，为了在 SlangPy 中使用自定义类型，需要显式导入。
import "slangpy";

// example.slang
struct Pixel
{
    float r;
    float g;
    float b;
};

// 将两个像素相加
Pixel add(Pixel a, Pixel b)
{
    Pixel result;
    result.r = a.r + b.r;
    result.g = a.g + b.g;
    result.b = a.b + b.b;
    return result;
}
```

创建并初始化缓冲区：

```python
# 创建两个尺寸为 16x16 的 2D 缓冲区
image_1 = spy.NDBuffer(device, dtype=module.Pixel, shape=(16, 16))
image_2 = spy.NDBuffer(device, dtype=module.Pixel, shape=(16, 16))

# 使用游标(cursor)填充第一个缓冲区
cursor_1 = image_1.cursor()
for x in range(16):
    for y in range(16):
        cursor_1[x + y * 16].write({
            'r': (x + y) / 32.0,
            'g': 0,
            'b': 0,
        })
cursor_1.apply()

# 直接从 NumPy 数组填充第二个缓冲区
image_2.copy_from_numpy(0.1 * np.random.rand(16 * 16 * 3).astype(np.float32))
```

调用函数：

```python
# 调用模块的 add 函数
result = module.add(image_1, image_2)
```

SlangPy 懂得这些缓冲区实际上是 `Pixel` 的 2D 数组。它推断出一个 2D 调度（在本例中为 16×16 个线程），其中每个线程从每个缓冲区读取一个 `Pixel`，将它们相加，然后将结果写入第三个缓冲区。

### 纹理 (Textures)

在这个示例中，我们将使用 SlangPy 对纹理进行读写操作，展示简单的广播（broadcasting）和 `inout` 参数的使用。

Slang 代码:

```slang
// 向给定像素添加一定数量（变亮）
void brighten(float4 amount, inout float4 pixel)
{
    pixel += amount;
}
```

生成并变亮纹理：

```python
# 生成随机图像
rand_image = np.random.rand(128 * 128 * 4).astype(np.float32) * 0.25
tex = device.create_texture(
    width=128,
    height=128,
    format=spy.Format.rgba32_float,
    usage=spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access,
    data=rand_image
)

# 用 tev 显示它
spy.tev.show(tex, name='photo')

# 调用模块的 brighten 函数，参数：
# - 广播到每个像素的 float4 常量
# - 作为 inout 参数的纹理
module.brighten(spy.float4(0.5), tex)

# 显示结果
spy.tev.show(tex, name='brighter')
```

在这个例子中：
- SlangPy 推断出一个 **2D 调度**，这是因为传入给函数的是一个 `float4` 的 2D 纹理。
- **第一个参数**（单个 `float4`）被**广播**给所有线程。
- **第二个参数**（被标记为 `inout`）允许对纹理进行读取和写入。

### 嵌套类型 (Nested Types)

SlangPy 支持多种将结构化数据传递给函数的方式。最简单的方法是通过 Python 字典进行传递。

传递字典的示例：

```slang
void copy(float4 src, out float4 dest)
{
    dest = src;
}
```

```python
# 使用字典嵌套将结构化的源值复制到纹理中
module.copy(
    src={
        'x': 1.0,
        'y': spy.rand_float(min=0, max=1, dim=1),
        'z': 0.0,
        'w': 1.0
    },
    dest=tex
)
```

在这里，`x`、`z` 和 `w` 被设置为常数值，而 `y` 被设置为一个 0 到 1 之间的随机浮点数。然而，它们也可以完全是 NumPy 数组、NDBuffers、甚至是（在这个场景中）1D 纹理！

对于需要明确类型信息的泛型或通用函数：

```python
# 使用 '_type' 显式声明类型
module.copy_vector(
    src={
        '_type': 'float4',
        'x': 1.0,
        'y': spy.rand_float(min=0, max=1, dim=1),
        'z': 0.0,
        'w': 1.0
    },
    dest=tex
)
```

`map` 方法是 SlangPy 在复杂场景中解析类型信息的主要机制：

```python
# 显式映射参数类型
module.copy_generic.map(src='float4', dest='float4')(
    src={
        'x': 1.0,
        'y': spy.rand_float(min=0, max=1, dim=1),
        'z': 0.0,
        'w': 1.0
    },
    dest=tex
)
```

### 类型方法 (Type Methods)

SlangPy 还可以调用 Slang 类型（不管是可变还是不可变的）的方法。这是通过以下两个关键类来实现的：
- `InstanceBuffer`: 表示在单个 `NDBuffer` 中存储的某种 Slang 类型的实例列表。
- `InstanceList`: 表示以 SOA（Structure of Arrays，数组结构体）形式存储的某种 Slang 类型的实例列表。

具有 Particle（粒子）类的示例：

```slang
import "slangpy";

struct Particle
{
    float3 position;
    float3 velocity;

    __init(float3 p, float3 v)
    {
        position = p;
        velocity = v;
    }

    [mutating]
    void update(float dt)
    {
        position += velocity * dt;
    }
};
```

创建和初始化粒子：

```python
# 创建粒子的缓冲区 (.as_struct 确保争取的 Python 类型提示)
particles = spy.InstanceBuffer(
    struct=module.Particle.as_struct(),
    shape=(10,)
)

# 构造位置为 (0, 0, 0) 并带有随机速度的粒子
particles.construct(
    p=spy.float3(0),
    v=spy.rand_float(-1, 1, 3)
)

# 使用 0.1 的时间增量 (dt) 更新粒子位置
particles.update(0.1)
```

### 广播 (Broadcasting)

SlangPy 的主要工作是获取一个为单一数据单元设计运行的函数，并将其转化为一个在并行的数据批次上运行的向量函数（vector function）。

广播相关术语：
- `维度 (Dimensionality)`: 一个值的维度数量。例如，1D 缓冲区的 `dimensionality` 为 1。
- `形状 (Shape)`: 某个值的每个维度的大小。比如，大小为 3 的 1D 缓冲区的 `shape` 是 (3,)。

广播过程：
1. 计算所有参数的最大 `dimensionality`（维度数量）。这决定了内核及其输出的 `dimensionality`。
2. 对于每个维度，所有的输入参数尺寸必须兼容。如果两个尺寸相等，或者是 1，表示它们兼容。
3. 如果某个维度的尺寸为 1，它就会被广播（broadcast）以匹配对应于其他参数的尺寸。

示例：

```python
# 所有维度均匹配
A       (10,3,4)
B       (10,3,4)
Out     (10,3,4)

# A 的第一维度是 1，因此被广播
A       (10,1,4)
B       (10,3,4)
Out     (10,3,4)

# 单个标量值被广播到输出的每一个维度
A       ()
B       (10,3,4)
Out     (10,3,4)
```

### 映射 (Mapping)

在 SlangPy 中，映射提供了一种精确控制参数维度与内核维度之间关系的机制。

基本映射示例：

```python
a = np.random.rand(10, 3, 4)
b = np.random.rand(10, 3, 4)
result = mymodule.add.map((0, 1, 2), (0, 1, 2))(a, b, _result='numpy')
```

具有不同维度参数的映射：

```python
a = np.random.rand(8, 8).astype(np.float32)
b = np.random.rand(8).astype(np.float32)

# 使用显式映射而非自动填充(auto-padding)：
result = mymodule.add.map(a=(0, 1), b=(1,))(a=a, b=b, _result='numpy')
```

数学外积计算示例：

```python
a = np.random.rand(10).astype(np.float32)
b = np.random.rand(20).astype(np.float32)

# 映射维度：
# - a 映射到维度 0 (尺寸 10)
# - b 映射到维度 1 (尺寸 20)
# 生成的内核和输出形状: (10, 20)
result = mymodule.multiply.map(a=(0,), b=(1,))(a=a, b=b, _result='numpy')
```

## 自动微分 (Auto-Differentiation)

### 基础自动微分

Slang 最强大的特性之一是它的自动微分功能。SlangPy 将此特性移植到了 Python 中，允许你轻松计算某个函数的导数。

一个可微分函数：

```slang
[Differentiable]
float polynomial(float a, float b, float c, float x) {
    return a * x * x + b * x + c;
}
```

注意该函数带有 `[Differentiable]` 属性，这告诉 Slang 生成反向传播 (backward propagation) 函数。

使用 Tensor（张量）类型：

```python
# 从一个 numpy 数组创建一个带有梯度的张量
x = spy.Tensor.numpy(device, np.array([1, 2, 3, 4], dtype=np.float32)).with_grads(zero=True)

# 评估多项式并请求张量作为返回值
result: spy.Tensor = module.polynomial(a=2, b=8, c=-1, x=x, _result='tensor')
print(result.to_numpy())
```

反向传播过程 (Backward pass)：

```python
# 为结果附加梯度，并在反向传播中将其设为 1
result = result.with_grads()
result.grad.storage.copy_from_numpy(np.array([1, 1, 1, 1], dtype=np.float32))

# 调用 module.polynomial 的 bwds (backwards 反向) 版本
module.polynomial.bwds(a=2, b=8, c=-1, x=x, _result=result)
print(x.grad.to_numpy())
```

在 SlangPy 中使用自动微分需要：
- 将你的函数标记为可微 (`Differentiable`)
- 使用 `Tensor` 类型存储可微数据
- 调用 `bwds` 函数来计算梯度

### PyTorch 集成

切换到 PyTorch 及其自动梯度计算 (auto-grad) 功能是非常简单的。关键改变只是加载模块时的代码：

```python
# 加载采用 torch 封装的模块。
module = spy.TorchModule.load_from_file(device, "example.slang")
```

创建 PyTorch 张量：

```python
# 创建张量
x = torch.tensor([1, 2, 3, 4], dtype=torch.float32, device='cuda', requires_grad=True)
```

利用 PyTorch 自动求导运行内核：

```python
# 评估多项式。现在的返回值将默认为一个 torch 张量。
result = module.polynomial(a=2, b=8, c=-1, x=x)
print(result)

# 在结果上运行反向传播，此时使用结果梯度 result grad == 1
result.backward(torch.ones_like(result))
print(x.grad)
```

该方式可行的原因是采用包裹处理过的 PyTorch 模块，自动把原来对 `polynomial` 的调用包在了一个自定义的 autograd 函数里。

## 生成器 (Generators)

SlangPy 提供了一种在内核内部动态生成数据的方法，去除了必须把参数都放到缓冲或张量里提供的繁琐流程。这是利用生成器实现的。

目前可用的生成器：
- Call Id（调用 ID）
- Thread Id（线程 ID）
- Wang Hash（Wang 哈希方法）
- Rand float（随机浮点数）
- Grid（网格）

### Id 生成器

Id 生成器提供与当前线程关联的安全唯一的标识。

Call Id 示例：

```slang
int2 myfunc(int2 value) {
    return value;
}
```

```python
# 用 call IDs 填充一个 4x4 的 int2 numpy 数组
res = np.zeros((4,4,2), dtype=np.int32)
module.myfunc(spy.call_id(), _result=res)

# [ [ [0,0], [1,0], [2,0], [3,0] ], [ [0,1], [1,1], [2,1], [3,1] ], ...
print(res)
```

Thread Id 提供实际的调度 (dispatch) 硬件线程 ID：

```python
# 用 hardware thread IDs 填充一个 4x4 的 int3 numpy 数组
res = np.zeros((4,4,3), dtype=np.int32)
module.myfunc3d(spy.thread_id(), _result=res)
```

### 随机数生成器

Wang Hash 生成器返回整数哈希值：

```python
# 用随机整数哈希值填充一个 4x4 的 int2 numpy 数组
res = np.zeros((4, 4, 2), dtype=np.int32)
module.myfunc(spy.wang_hash(), _result=res)
```

Rand Float 基于 Wang hash 进行随机数生成：

```python
# 用随机值填充一个 4x4 的 float2 numpy 数组
res = np.zeros((4, 4, 2), dtype=np.float32)
module.myfuncfloat(spy.rand_float(min=0, max=10), _result=res)
```

### 网格生成器 (Grid Generator)

网格生成器能直接影响被传递进去的内核模块其被执行的形状空间：

```python
# 用 call IDs 填充一个 4x4 的 int2 numpy 数组
res = module.myfunc(spy.grid(shape=(4,4)), _result='numpy')
```

Grid 支持跨度/步长 (strides)：

```python
# 传递步长作参数并填充
res = module.myfunc(spy.grid(shape=(4,4), stride=(2,2)), _result='numpy')
```

Grid 允许维度中含有未定义尺寸值（设置为 -1）：

```python
# 使网格的大部分形状能够自动被推断，同时设定具体的固定步长
res = np.zeros((4, 4, 2), dtype=np.int32)
module.myfunc(spy.grid(shape=(-1,-1), stride=(4,4)), _result=res)
```

## API 参考 (API Reference)

该接口 API 参考文档是通过 Python 的函数字符串文档 (docstrings) 自动构建生成的，这些文档本质上都来自于底层 C++ API 的有关注释。

主 `slangpy` 模块里包括了所有要在加载与调用来自 Python 的 Slang 函数时必须涉及的类型构建。

`slangpy.reflection` 模块是一个封装层，针对通过 SlangPy 拿到的 Slang 接口属性提供封装，以便你获取其反射数据。它通常常被 SlangPy 内部用以审查 Slang 的程序代码结构。可通过获取 `Module.layout` 变量以调用相关反射信息。

`slangpy.bindings` 模块内置一些必需用来让 SlangPy 能兼容支持新的各 Python 基本类型的工具代码和适配器。SlangPy 的各项系统提供自带支持的原生类型组件，最终都是靠依赖上面所声明类的子模块开发得出的。
