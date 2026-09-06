"""配置加载 + 校验（public-api §6）。"""
from .schema import load_config, parse_config
from .validator import validate_config

__all__ = ["load_config", "parse_config", "validate_config"]
