# training-material-generator
基于 Python 的 Web 应用，对接 Jira Cloud + GitHub，半自动化地从 Jira Ticket / GitHub PR / 源代码中提取功能信息，生成以"业务价值与操作流程"为核心的培训材料（PPT + 视频脚本 + FAQ）

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)


## 🎯 功能特性

### 核心能力

- **Jira Cloud 集成** — 从 Epic/Story/Sub-task 中提取需求描述、验收标准、用户故事
- **GitHub 集成** — 从 PR/Commit/代码变更中还原用户操作路径
- **AI 业务分析** — 将技术描述自动翻译为业务语言，提炼业务价值和 Before/After 对比
- **代码变更分析** — 从前端组件/API 路由/权限注解中还原操作流程

### 输出格式

| 格式 | 说明 |
|------|------|
| 📊 **PPT 演示文稿** (.pptx) | 包含封面、更新概览、功能讲解、业务价值、操作步骤、角色总结、FAQ |
| 🎬 **视频脚本** (.md) | 每个功能的开场白、场景描述、操作步骤旁白、价值总结 |
| ❓ **FAQ 文档** (.md) | 按操作类/限制类/场景类/异常类分组的常见问题 |

## 📁 项目结构

```
training-material-generator/
├── run.py                          # 一键启动入口
├── models.py                       # 核心数据模型
├── orchestrator.py                 # 编排器（串联所有模块）
├── adapters/
│   ├── jira_adapter.py             # Jira Cloud 数据提取
│   └── github_adapter.py           # GitHub 数据提取
├── analyzers/
│   ├── code_analyzer.py            # 代码变更分析（还原操作流程）
│   └── ai_analyzer.py              # AI 分析引擎（业务价值翻译）
├── generators/
│   ├── ppt_generator.py            # PPT 生成器
│   ├── video_script_generator.py   # 视频脚本生成器
│   └── faq_generator.py            # FAQ 生成器
├── web/
│   └── app.py                      # Streamlit Web 界面
├── sample_output.pptx              # 示例 PPT 输出
├── sample_video_script.md          # 示例视频脚本输出
└── sample_faq.md                   # 示例 FAQ 输出

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Jira Cloud 账号 + API Token
- GitHub 账号 + Personal Access Token
- OpenAI API Key（可选，用于 AI 业务分析）

### 安装

```bash
# 克隆项目
git clone <your-repo-url>
cd training-material-generator

# 安装依赖（Streamlit 会自动安装）
pip install streamlit jira PyGithub openai python-pptx --break-system-packages
```

### 启动

```bash
python run.py
# 或直接
streamlit run web/app.py
```

浏览器打开 `http://localhost:8501` 即可使用。

---

## 📖 使用流程

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1  配置集成                                            │
│  ├── Jira Cloud（Epic/Story 提取）                            │
│  ├── GitHub（PR/代码变更提取）                                 │
│  └── AI 引擎（业务价值翻译）                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2  输入数据源                                          │
│  ├── Jira Epic 模式：输入 Epic Key（如 PROJ-123）            │
│  ├── GitHub PR 模式：输入仓库名 + PR 编号                      │
│  └── 手动输入模式：直接录入功能信息                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3  自动分析                                            │
│  ├── 从 Jira 提取需求、AC、用户故事                           │
│  ├── 从 GitHub 提取 PR 描述和代码变更                         │
│  ├── 从代码还原 UI 交互和操作路径                              │
│  └── AI 提炼业务价值、生成 FAQ                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4  预览编辑                                            │
│  ├── 功能预览页：查看提取的功能清单                            │
│  ├── 业务价值页：编辑 Before/After 和价值主张                 │
│  ├── 操作流程页：确认操作步骤                                 │
│  └── FAQ 页：查看/补充常见问题                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5  导出下载                                            │
│  ├── 📊 PPT 演示文稿（可选自定义模板）                        │
│  ├── 🎬 视频脚本                                             │
│  └── ❓ FAQ 文档                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 PPT 模板功能

支持上传自定义 PPT 模板，自动将内容映射到模板页面：

1. 展开侧边栏「📊 PPT 模板」
2. 上传 `.pptx` 格式的模板文件
3. 配置页面映射（指定每种内容类型使用模板的哪个布局）
4. 可选：自定义主色调和强调色
5. 保存配置后，生成 PPT 时自动应用模板

---

## 🛠️ 模块说明

### 数据提取层 (`adapters/`)

| 模块 | 数据源 | 提取内容 |
|------|--------|---------|
| `jira_adapter.py` | Jira Cloud API | Epic → Story → Sub-task、AC、Comments |
| `github_adapter.py` | GitHub REST API | PR 描述、Commit、文件变更列表 |

### 分析层 (`analyzers/`)

| 模块 | 功能 |
|------|------|
| `code_analyzer.py` | 分析前端组件变更、API 路由、权限注解，还原操作流程 |
| `ai_analyzer.py` | 调用 LLM 将技术描述翻译为业务价值，生成 FAQ |

### 生成层 (`generators/`)

| 模块 | 输出 |
|------|------|
| `ppt_generator.py` | PPT 演示文稿（支持模板） |
| `video_script_generator.py` | 视频旁白脚本（Markdown） |
| `faq_generator.py` | FAQ 文档（Markdown） |

---
