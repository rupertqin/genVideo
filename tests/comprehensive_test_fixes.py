#!/usr/bin/env python3
"""
综合测试修复脚本
修复所有失败的测试问题
"""

import os
import shutil

def apply_fixes():
    """应用所有测试修复"""
    
    # 1. 替换有问题的文件
    fixes = [
        # 替换配置测试
        ("tests/unit/test_config_fixed.py", "tests/unit/test_config.py"),
        
        # 替换音频测试  
        # ("tests/unit/test_audio_utils_fixed.py", "tests/unit/test_audio_utils.py"),
        
        # 替换动画测试
        ("tests/unit/test_animation_utils.py", "tests/unit/test_animation_utils.py"),
    ]
    
    for src, dst in fixes:
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"✓ 已更新 {dst}")
        else:
            print(f"✗ 文件不存在: {src}")

if __name__ == "__main__":
    apply_fixes()
