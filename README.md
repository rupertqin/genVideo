# genVideo - 智能图片轮播视频生成器

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://python.org)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.0.0%2B-green.svg)](https://github.com/Zulko/moviepy)
[![PyAV](https://img.shields.io/badge/PyAV-10.0.0%2B-orange.svg)](https://github.com/PyAV-Org/PyAV)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25-yellow.svg)](tests/TESTING_REPORT.md)

genVideo 是一个基于 MoviePy 和 PyAV 的智能图片轮播视频生成工具。它能够自动将图片、音频等素材合成为具有专业效果的轮播视频，支持多种动画过渡效果和自定义配置。

## ✨ 主要功能

- 🎬 **智能轮播**: 自动检测音频停顿点，智能分配图片展示时间
- 🎵 **音频同步**: 完美匹配视频与音频时长，确保音画同步
- 🎨 **动画效果**: 支持缩放、平移等多种动画效果，可随机或固定配置
- 🔄 **过渡效果**: 内置淡入淡出过渡，营造流畅的视觉体验
- 📱 **多尺寸支持**: 支持横屏、竖屏、方形等多种视频尺寸预设
- ⚡ **高性能**: 使用 PyAV 进行音频分析，避免频繁调用 ffmpeg 命令行
- 🎯 **智能适配**: 自动循环使用图片以覆盖所有音频段落

## 📋 系统要求

- Python 3.7+
- macOS / Linux / Windows
- FFmpeg (MoviePy 依赖)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd genVideo

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 准备素材

```
genVideo/
├── images/          # 放置你的图片文件 (支持 jpg, png, jpeg)
├── audio.wav        # 音频文件 (或 audio.mp3)
└── generate.py      # 主程序
```

### 3. 生成视频

```bash
# 使用默认配置生成视频
python generate.py

# 指定输出文件和尺寸
python generate.py --output my_video.mp4 --size HD_720P

# 禁用动画效果
python generate.py --no-animation

# 查看所有可用尺寸
python generate.py --list-sizes
```

## 📖 详细使用说明

### 基本用法

#### 1. 准备素材

将图片文件放入 `images/` 目录，音频文件放在项目根目录（命名为 `audio.wav` 或 `audio.mp3`）。

支持的图片格式：

- JPG/JPEG
- PNG
- BMP
- TIFF

#### 2. 运行生成

```bash
python generate.py
```

程序会自动：

- 扫描 `images/` 目录中的图片
- 查找音频文件（优先 `audio.wav`，其次 `audio.mp3`）
- 分析音频时长和停顿点
- 生成轮播视频 `generated.mp4`

### 高级配置

#### 视频尺寸设置

```bash
# 使用预设尺寸
python generate.py --size HD_720P          # 1280x720
python generate.py --size PORTRAIT_1080P   # 1080x1920 (竖屏)
python generate.py --size SQUARE_1080      # 1080x1080 (方形)

# 自定义尺寸
python generate.py --size 1920x1080

# 测试尺寸（快速预览）
python generate.py --size TEST_SMALL       # 480x360
```

#### 动画和过渡效果

```bash
# 启用随机动画（默认）
python generate.py

# 禁用所有动画
python generate.py --no-animation

# 调整过渡效果时长
python generate.py --transition 0.5        # 0.5秒过渡
python generate.py --transition 2.0        # 2秒过渡
```

#### 性能和输出控制

```bash
# 指定输出文件
python generate.py --output my_video.mp4

# 调整帧率
python generate.py --fps 30                # 30fps（更流畅）
python generate.py --fps 15                # 15fps（文件更小）

# 指定图片目录
python generate.py --images ./my_images

# 指定音频文件
python generate.py --audio ./my_audio.mp3
```

### 可用的视频尺寸预设

#### 横屏尺寸

- `HD_720P` (1280×720) - 标准高清
- `FULL_HD_1080P` (1920×1080) - 全高清
- `UHD_4K` (3840×2160) - 4K 超高清
- `WIDESCREEN_2K` (2560×1440) - 2K 宽屏

#### 竖屏尺寸（适合短视频平台）

- `PORTRAIT_720P` (720×1280) - 竖屏 720P
- `PORTRAIT_1080P` (1080×1920) - 竖屏 1080P

#### 方形尺寸（适合 Instagram）

- `SQUARE_720` (720×720) - 方形 720
- `SQUARE_1080` (1080×1080) - 方形 1080

#### 测试尺寸

- `TEST_SMALL` (480×360) - 小尺寸测试
- `TEST_MEDIUM` (640×480) - 中等测试尺寸

## 🧪 测试说明

### 测试结构

项目包含完整的测试套件，分为单元测试和集成测试：

```
tests/
├── unit/                     # 单元测试
│   ├── test_config.py       # 配置模块测试
│   ├── test_audio_utils.py  # 音频工具测试
│   ├── test_image_utils.py  # 图片工具测试
│   ├── test_video_utils.py  # 视频工具测试
│   ├── test_slideshow_utils.py # 轮播控制器测试
│   └── test_animation_utils.py # 动画工具测试
├── integration/              # 集成测试
│   └── test_generate_workflow.py # 端到端工作流测试
└── pytest.ini              # pytest 配置
```

### 运行测试

#### 基本测试命令

```bash
# 运行所有测试
python -m pytest tests/

# 运行单元测试
python -m pytest tests/unit/

# 运行集成测试
python -m pytest tests/integration/

# 生成覆盖率报告
python -m pytest tests/ --cov --cov-report=html

# 查看覆盖率报告（HTML格式）
open htmlcov/index.html  # macOS
# 或在浏览器中打开 htmlcov/index.html
```

#### 高级测试选项

```bash
# 详细输出
python -m pytest tests/ -v

# 只运行快速测试（排除slow标记）
python -m pytest tests/ -m "not slow"

# 运行特定测试文件
python -m pytest tests/unit/test_config.py

# 在第一个失败时停止
python -m pytest tests/ -x

# 并行运行（需要 pytest-xdist）
python -m pytest tests/ -n auto
```

### 测试覆盖率

当前测试覆盖率：**80.94%**

#### 各模块覆盖率详情

| 模块                     | 覆盖率 | 状态      |
| ------------------------ | ------ | --------- |
| config.py                | 100%   | ✅ 优秀   |
| utils/image_utils.py     | 100%   | ✅ 优秀   |
| utils/video_utils.py     | 100%   | ✅ 优秀   |
| utils/slideshow_utils.py | 91%    | ✅ 良好   |
| utils/animation_utils.py | 82%    | ✅ 良好   |
| utils/audio_utils.py     | 44%    | ⚠️ 待改进 |

### 测试标记

项目使用 pytest 标记来分类测试：

```python
@pytest.mark.unit          # 单元测试
@pytest.mark.integration   # 集成测试
@pytest.mark.slow          # 慢速测试
@pytest.mark.requires_images   # 需要图片文件
@pytest.mark.requires_audio    # 需要音频文件
```

### 添加新测试

#### 单元测试示例

```python
import pytest
from utils.your_module import your_function

@pytest.mark.unit
def test_your_function():
    """测试你的函数"""
    result = your_function("test_input")
    assert result == "expected_output"
```

#### 集成测试示例

```python
import pytest
from generate import create_slideshow

@pytest.mark.integration
@pytest.mark.requires_images
@pytest.mark.requires_audio
def test_generate_video_workflow():
    """测试视频生成完整工作流"""
    # 测试代码
    pass
```

## ⚙️ 配置说明

### VideoSize 预设类

在 `config.py` 中定义了所有可用的视频尺寸预设：

```python
from config import VideoSize, parse_video_size

# 使用预设
size = VideoSize.HD_720P  # (1280, 720)

# 解析字符串
size = parse_video_size("PORTRAIT_1080P")  # (1080, 1920)

# 解析自定义格式
size = parse_video_size("1920x1080")  # (1920, 1080)
```

### 动画配置

```python
from utils.animation_utils import AnimationConfig, EasingCurve

# 创建自定义动画配置
config = AnimationConfig(
    animation_type="zoom",
    intensity=0.2,
    easing=EasingCurve.EASE_IN_OUT_QUAD
)
```

## 🔧 开发指南

### 项目结构

```
genVideo/
├── README.md              # 项目说明文档
├── AGENTS.md              # 项目目标和依赖说明
├── requirements.txt       # Python 依赖
├── config.py             # 配置管理
├── generate.py           # 主程序入口
├── play.py               # 播放脚本（如有）
├── utils/                # 工具模块
│   ├── audio_utils.py    # 音频处理工具
│   ├── image_utils.py    # 图片处理工具
│   ├── video_utils.py    # 视频处理工具
│   ├── slideshow_utils.py # 轮播控制器
│   └── animation_utils.py # 动画效果工具
├── tests/                # 测试目录
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   ├── data/             # 测试数据
│   ├── fixtures/         # 测试夹具
│   └── TESTING_REPORT.md # 测试报告
└── images/               # 示例图片目录
```

### 添加新功能

1. **添加新的视频尺寸预设**：

   ```python
   # 在 config.py 中添加
   MY_CUSTOM_SIZE = (1024, 768)
   ```

2. **添加新的动画效果**：

   ```python
   # 在 utils/animation_utils.py 中扩展
   class AnimationType:
       MY_NEW_ANIMATION = "my_new_animation"
   ```

3. **添加新的工具函数**：
   ```python
   # 在相应的 utils/*.py 中添加
   def my_new_function():
       """新功能说明"""
       pass
   ```

### 代码规范

- 遵循 PEP 8 代码风格
- 添加类型注解
- 编写文档字符串
- 为新功能添加测试
- 确保测试覆盖率不低于 80%

## 🐛 故障排除

### 常见问题

#### 1. 找不到图片文件

```
错误: 未在目录 `images` 中找到图片
```

**解决方案**：

- 检查 `images/` 目录是否存在
- 确保图片文件格式正确（jpg, png, jpeg, bmp, tiff）
- 使用 `--images` 参数指定正确的图片目录

#### 2. 找不到音频文件

```
错误: 未找到 `audio.wav` 或 `audio.mp3`
```

**解决方案**：

- 在项目根目录放置音频文件，命名为 `audio.wav` 或 `audio.mp3`
- 使用 `--audio` 参数指定音频文件路径

#### 3. MoviePy 版本兼容性

```
AttributeError: module 'moviepy' has no attribute 'VideoFileClip'
```

**解决方案**：

```bash
# 升级到最新版本
pip install --upgrade moviepy

# 或安装特定版本
pip install moviepy==2.0.0
```

#### 4. PyAV 音频处理问题

**解决方案**：

```bash
# 升级 PyAV
pip install --upgrade av

# 如果仍有问题，重新安装
pip uninstall av
pip install av
```

#### 5. FFmpeg 路径问题

**解决方案**：

```bash
# 安装 FFmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (使用 conda)
conda install ffmpeg
```

### 调试模式

启用详细日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 性能优化

### 提升生成速度

1. **使用较小的测试尺寸进行预览**：

   ```bash
   python generate.py --size TEST_SMALL
   ```

2. **降低帧率**：

   ```bash
   python generate.py --fps 15
   ```

3. **禁用动画效果**：

   ```bash
   python generate.py --no-animation
   ```

4. **减少过渡效果时长**：
   ```bash
   python generate.py --transition 0.3
   ```

### 内存优化

- 对于大量图片，使用较小的测试尺寸进行调试
- 分批处理大量素材
- 及时释放不需要的视频片段对象

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 贡献流程

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

### 提交规范

- **feat**: 新功能
- **fix**: 修复 bug
- **docs**: 文档更新
- **test**: 测试相关
- **refactor**: 代码重构
- **style**: 代码格式调整

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [MoviePy](https://github.com/Zulko/moviepy) - 强大的 Python 视频处理库
- [PyAV](https://github.com/PyAV-Org/PyAV) - Python 的 FFmpeg 绑定
- [NumPy](https://numpy.org/) - 科学计算基础库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](../../issues)
- 发送邮件至：[your-email@example.com]

---

⭐ 如果这个项目对你有帮助，请给个 Star！
