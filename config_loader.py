# config_loader.py
import json
import os
import sys
from typing import Dict, Any, Union, List


def _base_dir() -> str:
    """资源读取目录：打包后为 _MEIPASS，开发时为脚本目录"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _work_dir() -> str:
    """可写工作目录：打包后为 exe 所在目录，开发时为脚本目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class ConfigLoader:
    _instance = None
    config: Dict[str, Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._raw_config = cls._load_raw_config()
            cls.config = cls._filter_comments(cls._raw_config)
            cls._validate_paths()
            cls._validate_timing()
        return cls._instance

    @classmethod
    def _load_raw_config(cls) -> Dict[str, Any]:
        """加载原始配置文件（含注释）"""
        try:
            config_path = os.path.join(_base_dir(), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError("配置文件 config.json 未找到")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"配置文件格式错误: {str(e)} (位置：行{e.lineno}列{e.colno})")

    @classmethod
    def _filter_comments(cls, config: Union[Dict, List]) -> Union[Dict, List]:
        """递归过滤注释键"""
        if isinstance(config, dict):
            return {
                k: cls._filter_comments(v) 
                for k, v in config.items() 
                if not k.startswith('__comment__')
            }
        elif isinstance(config, list):
            return [cls._filter_comments(item) for item in config]
        return config

    @classmethod
    def _validate_paths(cls):
        """验证路径配置并创建必要目录"""
        base = _work_dir()
        required_dirs = [
            cls.get("paths", "screenshots"),
            cls.get("paths", "debug"),
            cls.get("paths", "button_images")
        ]
        for d in required_dirs:
            if not isinstance(d, str):
                raise ValueError(f"路径配置必须为字符串类型: {d}")
            os.makedirs(os.path.join(base, d), exist_ok=True)

    @classmethod
    def _validate_timing(cls):
        """深度验证时间配置有效性"""
        timing = cls.get("timing")
        
        # 验证最终检查延迟配置
        final_validation = timing.get("final_validation")
        if not final_validation:
            raise ValueError("缺失 final_validation 配置节")
            
        delay_range = final_validation.get("delay_range")
        if not isinstance(delay_range, list) or len(delay_range) != 2:
            raise ValueError("final_validation.delay_range 需要两个数值[最小, 最大]")
        if not all(isinstance(v, (int, float)) for v in delay_range):
            raise ValueError("delay_range 必须为数字类型")
        if delay_range[0] > delay_range[1]:
            raise ValueError("delay_range 最小值不能大于最大值")

        # 验证进程检查配置
        process_check = timing.get("process_check")
        if not process_check:
            raise ValueError("缺失 process_check 配置节")
            
        timeout = process_check.get("timeout")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("process_check.timeout 必须为大于0的数字")

        interval = process_check.get("interval")
        if not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError("process_check.interval 必须为大于0的数字")

    @classmethod
    def get(cls, *keys):
        """安全获取配置项（支持多级访问）"""
        try:
            value = cls.config
            for key in keys:
                if isinstance(value, list):
                    key = int(key)  # 处理列表索引
                value = value[key]
            return value
        except (KeyError, IndexError, TypeError) as e:
            key_path = '->'.join(map(str, keys))
            raise RuntimeError(f"配置项访问失败: {key_path} ({str(e)})")

# 初始化配置
config = ConfigLoader()