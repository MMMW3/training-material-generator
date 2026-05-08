"""
凭据管理工具
支持多种安全来源读取 API Key，按优先级：
  1. 环境变量（最安全，推荐生产环境使用）
  2. .env 文件（开发环境使用，已被 .gitignore 排除）
  3. Streamlit secrets.toml（Streamlit Cloud 部署时使用）
  4. Web 界面手动输入（兜底方案）
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 敏感信息脱敏：只显示前4位和后4位
SENSITIVE_KEYS = {
    "jira_token", "jira_api_token", "gh_token", "github_access_token",
    "ai_key", "openai_api_key", "api_key", "access_token", "api_token",
}


def mask_sensitive(value: str) -> str:
    """对敏感值进行脱敏处理"""
    if not value or len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def sanitize_exception(message: str) -> str:
    """脱敏异常信息中可能包含的凭据"""
    sanitized = message
    # 脱敏常见的 token/key 格式
    import re
    # sk-xxx 格式 (OpenAI)
    sanitized = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-****', sanitized)
    # ghp_xxx 格式 (GitHub)
    sanitized = re.sub(r'ghp_[a-zA-Z0-9]{20,}', 'ghp-****', sanitized)
    # Basic Auth 中的密码
    sanitized = re.sub(r'(Basic\s+[a-zA-Z0-9+=]+:)[a-zA-Z0-9+/=]+', r'\1****', sanitized)
    # Bearer Token
    sanitized = re.sub(r'(Bearer\s+)[a-zA-Z0-9._-]{20,}', r'\1****', sanitized)
    return sanitized


def load_env_file(env_path: Optional[str] = None):
    """
    加载 .env 文件（不依赖 python-dotenv，纯标准库实现）
    
    Args:
        env_path: .env 文件路径，默认为项目根目录下的 .env
    """
    if env_path is None:
        # 从当前文件向上查找项目根目录
        project_root = Path(__file__).parent.parent
        env_path = str(project_root / ".env")
    
    env_file = Path(env_path)
    if not env_file.exists():
        logger.debug(f".env 文件不存在: {env_path}")
        return
    
    logger.info(f"加载 .env 文件: {env_path}")
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            # 解析 KEY=VALUE
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # 环境变量未设置时才从 .env 加载（环境变量优先级更高）
                if key not in os.environ:
                    os.environ[key] = value
                    logger.debug(f"从 .env 加载: {key}={mask_sensitive(value)}")


def get_credential(key: str, st_secrets_fallback: bool = True) -> Optional[str]:
    """
    按优先级获取凭据：
    1. 环境变量
    2. Streamlit secrets（如果可用）
    
    Args:
        key: 凭据键名（如 "JIRA_API_TOKEN"）
        st_secrets_fallback: 是否尝试从 Streamlit secrets 读取
    
    Returns:
        凭据值，如果都不存在则返回 None
    """
    # 1. 环境变量（最高优先级）
    value = os.environ.get(key)
    if value:
        logger.debug(f"凭据 [{key}] 从环境变量获取")
        return value
    
    # 2. Streamlit secrets
    if st_secrets_fallback:
        try:
            import streamlit as st
            # Streamlit secrets 使用小写键名
            st_key = key.lower()
            if hasattr(st, 'secrets') and st_key in st.secrets:
                value = st.secrets[st_key]
                logger.debug(f"凭据 [{key}] 从 Streamlit secrets 获取")
                return value
        except Exception:
            pass
    
    return None


def get_jira_credentials() -> dict:
    """获取 Jira 凭据"""
    return {
        "email": get_credential("JIRA_EMAIL"),
        "api_token": get_credential("JIRA_API_TOKEN"),
        "server": get_credential("JIRA_SERVER", st_secrets_fallback=False) or "https://your-domain.atlassian.net",
    }


def get_github_credentials() -> dict:
    """获取 GitHub 凭据"""
    return {
        "access_token": get_credential("GITHUB_ACCESS_TOKEN"),
    }


def get_openai_credentials() -> dict:
    """获取 OpenAI 凭据"""
    return {
        "api_key": get_credential("OPENAI_API_KEY"),
        "base_url": get_credential("OPENAI_BASE_URL", st_secrets_fallback=False) or "https://api.openai.com/v1",
        "model": get_credential("OPENAI_MODEL", st_secrets_fallback=False) or "gpt-4o",
    }


def has_stored_credentials() -> dict:
    """检查哪些凭据已经通过环境变量/secrets 配置"""
    return {
        "jira": all(get_jira_credentials().values()),
        "github": bool(get_github_credentials()["access_token"]),
        "openai": bool(get_openai_credentials()["api_key"]),
    }


# 模块加载时自动尝试加载 .env
load_env_file()
