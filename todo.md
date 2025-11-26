# 视频生成脚本重构计划

## 目标

将 generate.py 中臃肿的代码抽离到模块化的工具类中，提高代码可维护性。

## 重构成果

### 1. 音频处理工具 (utils/audio_utils.py)

- [x] `get_audio_duration_ffmpeg()` - 获取音频时长
- [x] `get_audio_pauses()` - 检测音频停顿点

### 2. 图片处理工具 (utils/image_utils.py)

- [x] `get_image_paths()` - 获取图片路径集合
- [x] `get_audio_path()` - 获取音频文件路径

### 3. 轮播控制工具 (utils/slideshow_utils.py)

- [x] `SlideshowController` 类 - 控制图片轮播切换逻辑
- [x] 新增 `reset()` 方法 - 重置控制器状态
- [x] 新增 `get_remaining_changes()` 方法 - 获取剩余切换次数
- [x] 新增 `get_total_changes()` 方法 - 获取总切换次数

### 4. 重构主文件 (generate.py)

- [x] 导入工具模块
- [x] 保持 `create_slideshow()` 函数
- [x] 清理 if **name** == "**main**" 部分

## 重构收益

- ✅ 提高代码复用性
- ✅ 增强可测试性
- ✅ 便于维护和扩展
- ✅ 职责分离更清晰

## 新增文件结构

```
utils/
├── audio_utils.py      # 音频处理工具
├── image_utils.py      # 图片处理工具
└── slideshow_utils.py  # 轮播控制工具
```

## 测试状态

- ✅ 所有模块导入测试通过
- ✅ 语法检查通过
- ✅ 代码编译成功
