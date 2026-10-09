# genVideo - 智能图片轮播视频生成器

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://python.org)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.0.0%2B-green.svg)](https://github.com/Zulko/moviepy)
[![PyAV](https://img.shields.io/badge/PyAV-10.0.0%2B-orange.svg)](https://github.com/PyAV-Org/PyAV)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25-yellow.svg)](tests/TESTING_REPORT.md)

genVideo 是一个基于 MoviePy 和 PyAV 的智能图片/视频混合轮播视频生成工具。它能够自动将图片、视频、音频等素材合成为具有专业效果的轮播视频，支持多种动画过渡效果和自定义配置。

## ✨ 主要功能

- 🎬 **智能轮播**: 自动检测音频停顿点，智能分配媒体展示时间
- 🖼️ **视频支持**: 支持图片和视频混合轮播，视频自动循环播放
- 💬 **字幕烧录**: 基于 PyAV 解析 SRT 字幕并叠加到画面（硬字幕）
- 🎵 **音频同步**: 完美匹配视频与音频时长，确保音画同步
- 🎨 **动画效果**: 支持缩放、平移等多种动画效果，可随机或固定配置
- 🔄 **过渡效果**: 内置淡入淡出过渡，营造流畅的视觉体验
- 📱 **多尺寸支持**: 支持横屏、竖屏、方形等多种视频尺寸预设
- ⚡ **高性能**: 使用 PyAV 进行音频分析，避免频繁调用 ffmpeg 命令行
- 🎯 **智能适配**: 自动循环使用媒体以覆盖所有音频段落

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

默认目录约定（都在 `config.yaml` 里可改）：

```
genVideo/
├── assets/
│   ├── images/          # 图片 (jpg, jpeg, png, gif, webp, tiff, bmp)
│   │   ├── image1.jpg
│   │   └── image2.png
│   └── audio/           # 音频 audio.wav (或 audio.mp3)
│       ├── audio.wav
│       └── audio.srt    # 字幕与音频同名，自动配对
├── output/              # 生成结果（自动创建）
│   └── generated.mp4
├── config.yaml          # 配置（目录/尺寸/帧率/编码器/字幕样式）
└── generate.py          # 主程序
```

**字幕与音频按文件名配对**：`assets/audio/audio.wav` 自动使用 `assets/audio/audio.srt`；
音频叫 `第14节.wav` 就用 `第14节.srt`。名字不一致时在 `config.yaml` 写死：

```yaml
subtitle:
  path: assets/audio/017、第14节：资产配置的真正含义.srt
```

需要图片和视频混排时，在 `config.yaml` 里加一个视频目录：

```yaml
media:
  videos: assets/videos
```

兼容旧目录：默认的 `assets/images`、`assets/audio` 不存在时，会依次回退到
`media/`、`images/`（图片）和项目根目录（音频），并打印提示告诉你用了哪个、怎么迁移。

#### 从 CosyVoice 同步音频

若音频由 CosyVoice 生成，可用脚本一键拷贝到 `assets/audio/`（源目录读取 `.env` 的 `COSYVOICE_OUTPUT`）：

```bash
# 按 .env 配置同步
sh scripts/cp-audio.sh

# 或临时指定源目录
COSYVOICE_OUTPUT=/path/to/output sh scripts/cp-audio.sh
```

脚本会先校验 `audio.wav` 存在再拷贝（避免半套资源），并顺带同步 `audio.srt`（若存在，
字幕会被自动识别，无需额外配置）。

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

将图片放入 `assets/images/`，音频放入 `assets/audio/`（命名为 `audio.wav` 或 `audio.mp3`），
两个目录都可以在 `config.yaml` 的 `media` 区块里修改。

支持的媒体格式：

**图片格式**：
- JPG/JPEG
- PNG
- GIF
- WebP
- TIFF
- BMP

**视频格式**：
- MP4
- MOV
- AVI
- MKV
- WebM
- M4V
- FLV

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
# 为每张图片启用随机缩放/平移动画（Ken Burns 效果）
python generate.py --animation

# 不启用动画（默认行为，保留用于兼容）
python generate.py --no-animation

# 调整过渡效果时长
python generate.py --transition 0.5        # 0.5秒过渡
python generate.py --transition 2.0        # 2秒过渡
```

> 动画默认**关闭**：静态图片只做一次缩放裁剪后逐帧复用，速度最快。
> 开启 `--animation` 后，平移用纯 numpy 切片实现（几乎无额外开销），
> 缩放需要逐帧重采样（Ken Burns 必需），编码速度会有所下降。

#### 性能和输出控制

```bash
# 指定输出文件
python generate.py --output my_video.mp4

# 调整帧率
python generate.py --fps 30                # 30fps（更流畅）
python generate.py --fps 15                # 15fps（文件更小）

# 限制输出时长（同时截断音频，常用于快速试跑）
python generate.py --duration 00:03:00        # 3 分钟
python generate.py --duration 1:30            # 1 分 30 秒
python generate.py --duration 90              # 90 秒
python generate.py --duration 90s             # 带单位：90s / 3m / 1.5h
python generate.py --duration 00:01:30.250    # 精确到毫秒

# 指定图片目录
python generate.py --images ./my_images

# 指定视频目录（与图片一起轮播）
python generate.py --videos ./my_videos

# 图片和视频放在同一个目录（设置后忽略上面两项）
python generate.py --media ./my_media

# 指定音频：文件或目录皆可
python generate.py --audio ./my_audio.mp3
python generate.py --audio ./my_audio_dir
```

#### 视频处理

项目支持图片和视频混合轮播：

```bash
# 图片 + 视频目录（在 config.yaml 里配好，或用参数）
python generate.py --images ./images --videos ./videos

# 图片和视频放在同一个目录
python generate.py --media ./media
```

视频处理特性：
- 视频会自动循环播放以匹配分配的时长
- 视频会统一缩放到目标分辨率
- 图片和视频可以混合排序使用
- 动画效果仅应用于图片（视频保持原始播放）

#### 字幕叠加（硬字幕）

默认会自动查找与音频同名的字幕文件（如 `audio.wav` → `audio.srt`）并烧录到画面上；
无需字幕时加 `--no-subtitles` 关闭。

```bash
# 自动查找并叠加同名字幕
python generate.py

# 指定字幕文件
python generate.py --subtitles ./speech.srt

# 关闭字幕
python generate.py --no-subtitles

# 调整字幕样式
python generate.py --subtitle-size 40          # 字号（像素，默认按视频高度自适应）
python generate.py --subtitle-bottom 0.1       # 距底部比例（默认 0.08）
python generate.py --subtitle-font /path/to/font.ttf   # 指定字体（默认自动选系统中文字体）
```

实现说明：

- 字幕解析使用 **PyAV 的 Subtitle API**（`container.streams.subtitles` + `SubtitleStream.decode2`
  得到 `SubtitleSet`，读取 `AssSubtitle` 的文本与时间轴），无需额外第三方字幕库；
- 渲染使用 Pillow 生成带描边与半透明底色的 RGBA 图层，再由 MoviePy 按时间区间叠加到成片；
- 常见 PyAV 版本差异（如 16.x 的 `dialogue` 属性异常）已做回退兼容。

#### 编码器与码率（性能）

默认使用软件编码 `libx264`（`preset=veryfast`），跨平台、画质与体积可控。需要更快时可用硬件编码：

```bash
# macOS：VideoToolbox 硬件编码（约 1.5~2.4 倍）
python generate.py --encoder h264_videotoolbox

# 自动探测可用硬件编码器，探测不到则回退 libx264
python generate.py --encoder auto

# 软件编码速度档位（越快画质略降）
python generate.py --preset superfast

# 硬件编码器建议适当调高码率
python generate.py --encoder h264_videotoolbox --bitrate 12000k
```

为什么硬件编码不设为默认：`h264_videotoolbox` 仅 macOS 存在（Linux/Windows 是 `h264_nvenc` / `h264_qsv` / `h264_amf`），
直接写死会在其它平台报错；且同码率下画质与体积通常不如 libx264，输出还会随 GPU/驱动/系统版本变化、不易复现。
因此保留 libx264 为默认，需要时用 `--encoder auto` 自动探测并回退。

### 可用的视频尺寸预设

#### 横屏尺寸

- `HD_720P` (1280×720) - 标准高清
- `HD_1080P` (1920×1080) - 全高清
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

### config.yaml（推荐）

项目根目录的 `config.yaml` 保存各项默认值，**优先级：命令行参数 > config.yaml > 代码内置默认值**。

```yaml
video:
  size: HD_720P          # 尺寸预设或 "1280x720"
  fps: 24                # 帧率（总帧数 = 时长 x fps，直接影响耗时）
  duration: null         # 输出时长；null = 用完整音频（写法见下）
  transition: 1.0        # 媒体切换过渡时长（秒）
  encoder: libx264       # libx264 | h264_videotoolbox | ... | auto
  preset: veryfast       # 仅 libx264 生效
  bitrate: 5000k
  animation: false       # 图片是否加随机缩放/平移动画
  layout: fullscreen     # 画面布局组件：fullscreen | card

media:
  images: assets/images            # 图片目录
  videos: null                     # 视频目录（可选）
  dir: null                        # 混合目录（图片+视频放一起）；设置后忽略上面两项
  audio: assets/audio/audio.wav    # 音频完整路径（写目录则在该目录里找 audio.wav/audio.mp3）
  output: output/generated.mp4     # 输出文件（目录不存在会自动创建）

subtitle:
  enabled: true          # 是否叠加字幕
  path: null             # null = 自动查找与音频同名的 .srt
  font: null             # null = 自动选择系统中文字体
  size: null             # 字号（像素）；null = 按视频高度自适应（height x 0.05）

  bottom: 0.08           # 距底部高度比例
  max_width: 0.9         # 单行最大宽度比例，超出自动折行
  line_spacing: 1.25     # 行距倍数
  stroke_width: 3        # 描边宽度（像素）

  text_color: "#FFFFFF"  # "#RRGGBB" / "#RRGGBBAA" / [r, g, b]
  box_color: [0, 0, 0]   # 文字底色
  box_alpha: 150         # 底色透明度 0-255（0 = 只描边不画底色）
```

**输出时长** `video.duration` 支持多种写法（可精确到毫秒），留空即用完整音频：

```yaml
video:
  duration: 00:03:00        # 3 分钟；也可写 180 / 180.5 / 180s / 3m / 1.5h / 3:00 / 00:03:00.250
  # duration: null          # 不限制，用完整音频
```

只写想改的键即可，其余自动回落内置默认值。例如做竖屏短视频的字幕样式：

```yaml
subtitle:
  size: 48
  bottom: 0.12
  text_color: "#FFE066"
  box_color: [0, 0, 0]
  box_alpha: 180
```

命令行仍可临时覆盖其中几项（`--subtitle-size` / `--subtitle-font` / `--subtitle-bottom` / `--no-subtitles`）：

```bash
python generate.py --subtitle-size 20      # 只改这一项，其余沿用 config.yaml
```

> `config.yaml` 解析失败会直接报错并指出文件路径（不会静默忽略你的配置）。
> 读取它需要 `PyYAML`（已在 requirements.txt 中）。

### 画面布局组件

画面层是**可插拔的组件**，用 `video.layout` 切换（`--layout` 可临时覆盖）。
内置两个，字幕是另一个独立组件，始终叠加在上面：

| 组件 | 说明 |
|---|---|
| `fullscreen` | 全屏铺满：图片覆盖式缩放 + 居中裁剪（默认） |
| `card` | 卡片式：背景模糊压暗铺满 + 前景留边圆角卡片（不铺满）+ 标题 |

```yaml
video:
  layout: card           # fullscreen | card

layout:
  card:
    inset: 0.07             # 卡片四周留白（占短边比例）
    radius: 40              # 圆角半径（像素）
    shadow: 24              # 阴影模糊半径（0 = 不画）
    background_blur: 24     # 背景模糊半径（0 = 不模糊）
    background_darken: 0.35 # 背景压暗强度 0~1
    title: null             # 标题；null = 自动用音频文件名（去扩展名）
    title_size: 60
    title_color: "#FFFFFF"
    title_position: top     # top | bottom
```

```bash
# 标题不写时自动取音频文件名，例如「017、第14节：资产配置的真正含义」
python generate.py --layout card
```

**新增一个组件**：在 `utils/layouts.py` 里写一个函数（签名
`fn(source_image, video_size, duration, options) -> frame(t)`），用
`@register_layout("名字")` 注册即可，随后 `video.layout: 名字` 就能用。

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
├── config.yaml            # 用户配置（目录/尺寸/帧率/编码器/字幕样式）
├── config.py              # 配置管理（尺寸预设 + config.yaml 读取）
├── generate.py            # 主程序入口
├── play.py               # 播放脚本（如有）
├── assets/               # 素材（默认位置，可在 config.yaml 改）
│   ├── images/           # 图片
│   └── audio/            # 音频 audio.wav + 同名字幕 audio.srt
├── output/               # 生成结果（自动创建）
├── scripts/
│   └── cp-audio.sh        # 从 CosyVoice 同步音频与字幕到 assets/audio/
├── utils/                # 工具模块
│   ├── audio_utils.py    # 音频处理工具
│   ├── media_utils.py    # 媒体处理工具（图片+视频）
│   ├── image_utils.py    # 图片处理工具（兼容旧版）
│   ├── video_utils.py    # 视频处理工具
│   ├── subtitle_utils.py # 字幕解析与渲染
│   ├── layouts.py        # 画面布局组件（fullscreen / card，可插拔）
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
错误: 未找到图片目录 `assets/images`。
```

**解决方案**：

- 把图片放入 `assets/images/`，或在 `config.yaml` 里改 `media.images`
- 确保图片格式正确（jpg, jpeg, png, gif, webp, tiff, bmp）
- 临时指定：`--images ./my_images`
- 若你的图片在旧目录，可在 `config.yaml` 写 `media.images: media`

#### 2. 找不到音频文件

```
错误: 未找到音频文件（查找位置: `assets/audio/audio.wav`）。
```

**解决方案**：

- 把音频放到 `assets/audio/`，或在 `config.yaml` 的 `media.audio` 里写完整路径
- 临时指定：`--audio ./my_audio.mp3`（文件或目录都可以）
- 字幕需与音频同名（`xxx.wav` → `xxx.srt`），否则用 `subtitle.path` 指定

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
