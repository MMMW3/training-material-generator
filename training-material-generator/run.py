"""
培训材料生成器 - 启动入口
"""

import subprocess
import sys
import os


def install_dependencies():
    """安装依赖"""
    dependencies = [
        "streamlit",
        "jira",
        "PyGithub",
        "openai",
        "python-pptx",
    ]
    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_").replace("python_pptx", "pptx"))
        except ImportError:
            print(f"正在安装 {dep}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep, "--break-system-packages", "-q"]
            )


def main():
    """启动 Web 应用"""
    install_dependencies()

    # 项目根目录（run.py 所在目录）
    project_root = os.path.dirname(os.path.abspath(__file__))
    web_app = os.path.join(project_root, "web", "app.py")

    print("=" * 60)
    print("📚 培训材料生成器")
    print("=" * 60)
    print("正在启动 Web 应用...")
    print("请在浏览器中打开显示的地址")
    print("=" * 60)

    subprocess.check_call([sys.executable, "-m", "streamlit", "run", web_app, "--server.port", "8501"])


if __name__ == "__main__":
    main()
