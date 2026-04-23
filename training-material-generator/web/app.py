"""
培训材料生成器 - Streamlit Web 界面
提供可视化操作界面，支持配置、预览、编辑和导出
"""

import sys
import os
import json
import tempfile
import logging

# 确保模块导入路径：将项目根目录（web/ 的父目录）加入 sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st
from datetime import datetime

from models import (
    TrainingMaterial, FeatureInfo, FeaturePriority,
    BusinessValue, OperationFlow, FAQItem,
    PPTTemplateConfig, PageType,
)
from adapters.jira_adapter import JiraAdapter
from adapters.github_adapter import GitHubAdapter
from analyzers.code_analyzer import CodeAnalyzer
from analyzers.ai_analyzer import AIAnalyzer
from orchestrator import TrainingMaterialOrchestrator
from generators.ppt_generator import PPTGenerator
from generators.video_script_generator import VideoScriptGenerator
from generators.faq_generator import FAQGenerator

# 页面配置
st.set_page_config(
    page_title="培训材料生成器",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 自定义 CSS
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1F4E79;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: #fafafa;
    }
    .priority-P0 { border-left: 4px solid #e74c3c; }
    .priority-P1 { border-left: 4px solid #f39c12; }
    .priority-P2 { border-left: 4px solid #3498db; }
    .value-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .step-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 0.8rem;
    }
    .step-number {
        background: #1F4E79;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 0.8rem;
        flex-shrink: 0;
    }
    .faq-item {
        border-bottom: 1px solid #eee;
        padding: 0.8rem 0;
    }
    .faq-question {
        font-weight: 600;
        color: #1F4E79;
    }
    .faq-answer {
        color: #555;
        margin-top: 0.3rem;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """初始化 Session State"""
    if "material" not in st.session_state:
        st.session_state.material = None
    if "jira_adapter" not in st.session_state:
        st.session_state.jira_adapter = None
    if "github_adapter" not in st.session_state:
        st.session_state.github_adapter = None
    if "ai_analyzer" not in st.session_state:
        st.session_state.ai_analyzer = None
    if "step" not in st.session_state:
        st.session_state.step = "config"
    if "template_config" not in st.session_state:
        st.session_state.template_config = None
    if "template_file_path" not in st.session_state:
        st.session_state.template_file_path = None


def render_sidebar():
    """渲染侧边栏 - 配置面板"""
    with st.sidebar:
        st.title("⚙️ 配置面板")

        # ====== Jira 配置 ======
        st.subheader("🔗 Jira Cloud 配置")
        with st.expander("Jira 连接设置", expanded=False):
            jira_email = st.text_input("邮箱", key="jira_email", placeholder="your-email@company.com")
            jira_token = st.text_input("API Token", key="jira_token", type="password",
                                       placeholder="从 atlassian.com 获取")
            jira_server = st.text_input("服务器地址", key="jira_server",
                                        value="https://your-domain.atlassian.net")

            if st.button("测试 Jira 连接", key="test_jira"):
                if jira_email and jira_token:
                    try:
                        adapter = JiraAdapter(jira_email, jira_token, jira_server)
                        if adapter.test_connection():
                            st.success("✅ Jira 连接成功！")
                            st.session_state.jira_adapter = adapter
                        else:
                            st.error("❌ Jira 连接失败，请检查配置")
                    except Exception as e:
                        st.error(f"❌ 连接错误: {e}")
                else:
                    st.warning("请填写邮箱和 API Token")

        # ====== GitHub 配置 ======
        st.subheader("🐙 GitHub 配置")
        with st.expander("GitHub 连接设置", expanded=False):
            gh_token = st.text_input("Personal Access Token", key="gh_token", type="password",
                                     placeholder="ghp_xxxx")
            if st.button("测试 GitHub 连接", key="test_gh"):
                if gh_token:
                    try:
                        adapter = GitHubAdapter(gh_token)
                        if adapter.test_connection():
                            st.success("✅ GitHub 连接成功！")
                            st.session_state.github_adapter = adapter
                        else:
                            st.error("❌ GitHub 连接失败，请检查 Token")
                    except Exception as e:
                        st.error(f"❌ 连接错误: {e}")
                else:
                    st.warning("请填写 Access Token")

        # ====== AI 配置 ======
        st.subheader("🤖 AI 分析引擎配置")
        with st.expander("OpenAI API 设置", expanded=False):
            ai_key = st.text_input("API Key", key="ai_key", type="password",
                                   placeholder="sk-xxxx")
            ai_base_url = st.text_input("API Base URL", key="ai_base_url",
                                        value="https://api.openai.com/v1")
            ai_model = st.selectbox("模型", key="ai_model",
                                    options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"])

            if ai_key:
                st.session_state.ai_analyzer = AIAnalyzer(
                    api_key=ai_key,
                    base_url=ai_base_url,
                    model=ai_model,
                )

        # ====== PPT 模板配置 ======
        st.subheader("📊 PPT 模板配置")
        with st.expander("模板上传与设置", expanded=False):
            st.markdown("""
            **使用自定义 PPT 模板：**
            1. 上传 .pptx 格式的模板文件
            2. 配置页面映射关系
            3. 保存为默认模板
            """)
            
            # 模板文件上传
            uploaded_template = st.file_uploader(
                "上传 PPT 模板", 
                type=["pptx"],
                key="template_uploader",
                help="上传 .pptx 格式的 PowerPoint 模板文件"
            )
            
            if uploaded_template:
                # 保存上传的模板到临时目录
                template_dir = tempfile.mkdtemp()
                template_path = os.path.join(template_dir, "template.pptx")
                with open(template_path, "wb") as f:
                    f.write(uploaded_template.getvalue())
                st.session_state.template_file_path = template_path
                st.success(f"✅ 模板已上传: {uploaded_template.name}")
            
            # 显示当前模板状态
            if st.session_state.template_file_path:
                st.info(f"📄 当前模板: {os.path.basename(st.session_state.template_file_path)}")
            
            # 模板配置选项
            st.markdown("---")
            st.markdown("**页面映射配置**")
            st.markdown("将内容类型映射到模板的幻灯片布局索引")
            
            col_a, col_b = st.columns(2)
            with col_a:
                cover_layout = st.number_input("封面页布局", min_value=0, max_value=20, value=0, key="cover_layout")
                overview_layout = st.number_input("概览页布局", min_value=0, max_value=20, value=1, key="overview_layout")
                feature_layout = st.number_input("功能标题页布局", min_value=0, max_value=20, value=2, key="feature_layout")
                value_layout = st.number_input("业务价值页布局", min_value=0, max_value=20, value=3, key="value_layout")
            with col_b:
                flow_layout = st.number_input("操作流程页布局", min_value=0, max_value=20, value=4, key="flow_layout")
                role_layout = st.number_input("角色总结页布局", min_value=0, max_value=20, value=5, key="role_layout")
                faq_layout = st.number_input("FAQ页布局", min_value=0, max_value=20, value=6, key="faq_layout")
                end_layout = st.number_input("结束页布局", min_value=0, max_value=20, value=0, key="end_layout")
            
            # 配色配置
            st.markdown("---")
            st.markdown("**配色方案**（覆盖模板默认配色）")
            primary_color = st.color_picker("主色调", value="#1F4E79", key="primary_color_picker")
            accent_color = st.color_picker("强调色", value="#ED7D31", key="accent_color_picker")
            
            # 保存模板配置
            if st.button("💾 保存模板配置", use_container_width=True):
                if st.session_state.template_file_path:
                    page_mappings = {
                        PageType.COVER.value: cover_layout,
                        PageType.OVERVIEW.value: overview_layout,
                        PageType.FEATURE_TITLE.value: feature_layout,
                        PageType.BUSINESS_VALUE.value: value_layout,
                        PageType.OPERATION_FLOW.value: flow_layout,
                        PageType.ROLE_SUMMARY.value: role_layout,
                        PageType.FAQ.value: faq_layout,
                        PageType.END.value: end_layout,
                    }
                    
                    st.session_state.template_config = PPTTemplateConfig(
                        template_path=st.session_state.template_file_path,
                        template_name=os.path.basename(st.session_state.template_file_path),
                        page_mappings=page_mappings,
                        primary_color=primary_color.lstrip("#"),
                        accent_color=accent_color.lstrip("#"),
                        enabled=True,
                    )
                    st.success("✅ 模板配置已保存！")
                else:
                    st.warning("请先上传模板文件")
            
            # 清除模板配置
            if st.button("🗑️ 清除模板配置", use_container_width=True):
                st.session_state.template_config = None
                st.session_state.template_file_path = None
                st.info("模板配置已清除，将使用默认样式生成 PPT")
            
            # 显示当前配置状态
            if st.session_state.template_config:
                st.markdown("---")
                st.markdown("**当前模板配置：**")
                config = st.session_state.template_config
                st.json({
                    "模板名称": config.template_name,
                    "启用状态": config.enabled,
                    "主色调": f"#{config.primary_color}",
                    "强调色": f"#{config.accent_color}",
                    "页面映射": config.page_mappings,
                })

        st.divider()

        # ====== 导航 ======
        st.subheader("📑 导航")
        nav_options = {
            "config": "📋 配置与输入",
            "preview": "👁️ 功能预览",
            "value": "💡 业务价值",
            "flow": "📝 操作流程",
            "faq": "❓ FAQ",
            "export": "📤 导出下载",
        }
        for key, label in nav_options.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.step = key


def render_config_page():
    """渲染配置与输入页面"""
    st.markdown('<div class="main-header">📚 培训材料生成器</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">从 Jira/GitHub/代码 自动生成用户培训材料</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 数据源配置")

        # 数据源选择
        data_source = st.radio("选择数据源", ["Jira Epic", "仅 GitHub PR", "手动输入"], horizontal=True)

        if data_source == "Jira Epic":
            epic_key = st.text_input("Jira Epic Key", placeholder="PROJ-123")
            github_repo = st.text_input("GitHub 仓库（可选）", placeholder="owner/repo")
            pr_numbers_text = st.text_input("关联 PR 编号（可选，逗号分隔）", placeholder="101, 102, 103")
            pr_numbers = [int(n.strip()) for n in pr_numbers_text.split(",") if n.strip().isdigit()] if pr_numbers_text else []

            if st.button("🚀 开始生成", type="primary", use_container_width=True):
                if not epic_key:
                    st.error("请输入 Jira Epic Key")
                    return
                _run_generation(
                    epic_key=epic_key,
                    github_repo=github_repo or None,
                    github_pr_numbers=pr_numbers or None,
                )

        elif data_source == "仅 GitHub PR":
            github_repo = st.text_input("GitHub 仓库", placeholder="owner/repo")
            pr_numbers_text = st.text_input("PR 编号（逗号分隔）", placeholder="101, 102, 103")
            pr_numbers = [int(n.strip()) for n in pr_numbers_text.split(",") if n.strip().isdigit()] if pr_numbers_text else []

            if st.button("🚀 开始生成", type="primary", use_container_width=True):
                if not github_repo or not pr_numbers:
                    st.error("请填写仓库和 PR 编号")
                    return
                _run_generation_github_only(github_repo, pr_numbers)

        else:
            st.info("手动输入模式：直接输入功能信息，不连接外部系统")
            st.subheader("添加功能")

            if "manual_features" not in st.session_state:
                st.session_state.manual_features = []

            feature_name = st.text_input("功能名称", key="manual_name")
            feature_desc = st.text_area("功能描述", key="manual_desc")
            feature_priority = st.selectbox("优先级", [p.value for p in FeaturePriority], key="manual_priority")

            if st.button("➕ 添加功能", use_container_width=True):
                if feature_name:
                    st.session_state.manual_features.append({
                        "name": feature_name,
                        "description": feature_desc,
                        "priority": feature_priority,
                    })
                    st.success(f"已添加功能：{feature_name}")
                    st.rerun()

            # 显示已添加的功能
            for i, feat in enumerate(st.session_state.manual_features):
                st.markdown(f"**{feat['name']}** ({feat['priority']}) — {feat['description'][:50]}")

            if st.session_state.manual_features and st.button("🚀 生成培训材料", type="primary", use_container_width=True):
                _run_generation_manual()

    with col2:
        st.subheader("📋 版本信息")
        version = st.text_input("版本号", value=datetime.now().strftime("%Y.%m.%d"))
        release_date = st.text_input("发布日期", value=datetime.now().strftime("%Y年%m月%d日"))

        st.subheader("ℹ️ 使用说明")
        st.markdown("""
        **工作流程：**

        1️⃣ **配置连接** — 在左侧配置 Jira/GitHub/AI 的连接信息

        2️⃣ **输入信息** — 填写 Epic Key 或 PR 编号

        3️⃣ **自动分析** — 系统自动提取信息并用 AI 分析业务价值

        4️⃣ **预览编辑** — 在各页面预览并编辑生成的内容

        5️⃣ **导出下载** — 导出 PPT、视频脚本、FAQ 文档

        ---

        **支持的输出格式：**
        - 📊 PPT 演示文稿 (.pptx)
        - 🎬 视频脚本 (.md)
        - ❓ FAQ 文档 (.md)
        """)


def _run_generation(epic_key, github_repo=None, github_pr_numbers=None):
    """执行从 Jira Epic 生成"""
    with st.spinner("正在提取信息并分析..."):
        try:
            orchestrator = TrainingMaterialOrchestrator(
                jira_adapter=st.session_state.jira_adapter,
                github_adapter=st.session_state.github_adapter,
                ai_analyzer=st.session_state.ai_analyzer,
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                material = orchestrator.generate_from_jira_epic(
                    epic_key=epic_key,
                    github_repo=github_repo,
                    github_pr_numbers=github_pr_numbers,
                    output_dir=tmpdir,
                )
                st.session_state.material = material
                st.session_state.output_dir = tmpdir
                st.session_state.step = "preview"
                st.success("✅ 培训材料生成成功！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 生成失败: {e}")


def _run_generation_github_only(github_repo, pr_numbers):
    """执行从 GitHub PR 生成"""
    with st.spinner("正在提取信息并分析..."):
        try:
            orchestrator = TrainingMaterialOrchestrator(
                github_adapter=st.session_state.github_adapter,
                ai_analyzer=st.session_state.ai_analyzer,
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                material = orchestrator.generate_from_github_only(
                    github_repo=github_repo,
                    pr_numbers=pr_numbers,
                    output_dir=tmpdir,
                )
                st.session_state.material = material
                st.session_state.output_dir = tmpdir
                st.session_state.step = "preview"
                st.success("✅ 培训材料生成成功！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 生成失败: {e}")


def _run_generation_manual():
    """执行手动输入生成"""
    with st.spinner("正在分析..."):
        try:
            features = []
            for feat in st.session_state.manual_features:
                features.append(FeatureInfo(
                    name=feat["name"],
                    description=feat["description"],
                    priority=FeaturePriority(feat["priority"]),
                ))

            material = TrainingMaterial(
                version=datetime.now().strftime("%Y-%m-%d"),
                release_date=datetime.now().strftime("%Y年%m月%d日"),
                features=features,
                summary=f"本次更新包含 {len(features)} 个功能变更。",
            )

            # AI 分析（如果配置了）
            if st.session_state.ai_analyzer:
                material.summary = st.session_state.ai_analyzer.generate_summary(features)
                for feature in features:
                    bv = st.session_state.ai_analyzer.analyze_business_value(feature)
                    material.business_values[feature.name] = bv
                    faqs = st.session_state.ai_analyzer.generate_faqs(feature, bv)
                    material.faqs.extend(faqs)

            st.session_state.material = material
            st.session_state.step = "preview"
            st.success("✅ 培训材料生成成功！")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 生成失败: {e}")


def render_preview_page():
    """渲染功能预览页面"""
    material = st.session_state.material
    if not material:
        st.warning("请先生成培训材料")
        return

    st.title("👁️ 功能预览")
    st.markdown(f"**版本：** {material.version} | **日期：** {material.release_date}")
    st.markdown(f"### 📋 更新概览\n{material.summary}")

    st.divider()

    for feature in material.features:
        priority_class = f"priority-{feature.priority.value[:2]}"
        st.markdown(f"""
        <div class="feature-card {priority_class}">
            <h3>{feature.name}</h3>
            <p><strong>优先级：</strong>{feature.priority.value}</p>
            <p>{feature.description}</p>
            {"<p><strong>目标用户：</strong>" + "、".join(feature.target_audience) + "</p>" if feature.target_audience else ""}
            {"<p><strong>涉及模块：</strong>" + "、".join(feature.affected_modules) + "</p>" if feature.affected_modules else ""}
        </div>
        """, unsafe_allow_html=True)


def render_value_page():
    """渲染业务价值页面"""
    material = st.session_state.material
    if not material:
        st.warning("请先生成培训材料")
        return

    st.title("💡 业务价值分析")

    for feature in material.features:
        bv = material.business_values.get(feature.name)
        if not bv:
            st.info(f"功能「{feature.name}」暂无业务价值分析（需要配置 AI 引擎）")
            continue

        with st.expander(f"🎯 {feature.name}", expanded=True):
            st.markdown(f"""
            <div class="value-box">
                <h3>核心价值</h3>
                <p>{bv.value_proposition}</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### ❌ 使用前")
                st.write(bv.before_scenario)
            with col2:
                st.markdown("#### ✅ 使用后")
                st.write(bv.after_scenario)

            st.markdown(f"**解决的痛点：** {bv.problem_statement}")

            if bv.target_audience:
                st.markdown(f"**目标用户：** {'、'.join(bv.target_audience)}")

            if bv.key_benefits:
                st.markdown("**关键收益：**")
                for benefit in bv.key_benefits:
                    st.markdown(f"- ✅ {benefit}")


def render_flow_page():
    """渲染操作流程页面"""
    material = st.session_state.material
    if not material:
        st.warning("请先生成培训材料")
        return

    st.title("📝 操作流程")

    for feature in material.features:
        flow = material.operation_flows.get(feature.name)
        if not flow:
            st.info(f"功能「{feature.name}」暂无操作流程（需要 GitHub 代码变更信息）")
            continue

        with st.expander(f"📋 {feature.name}", expanded=True):
            st.markdown(f"**功能入口：** {flow.entry_point}")

            for step in flow.steps:
                st.markdown(f"""
                <div class="step-item">
                    <div class="step-number">{step.step_number}</div>
                    <div>
                        <strong>{step.action}</strong><br>
                        <span style="color:#666">{step.description}</span><br>
                        <span style="color:#2E75B6">→ {step.expected_result}</span>
                        {"<br><span style='color:#999'>📸 " + step.screenshot_hint + "</span>" if step.screenshot_hint else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if flow.notes:
                st.markdown("---")
                st.markdown("**⚠️ 注意事项：**")
                for note in flow.notes:
                    st.warning(note)


def render_faq_page():
    """渲染 FAQ 页面"""
    material = st.session_state.material
    if not material:
        st.warning("请先生成培训材料")
        return

    st.title("❓ 常见问题 (FAQ)")

    if not material.faqs:
        st.info("暂无 FAQ（需要配置 AI 引擎）")
        return

    # 按分类分组
    from collections import defaultdict
    faq_by_category = defaultdict(list)
    for faq in material.faqs:
        faq_by_category[faq.category].append(faq)

    category_icons = {"操作类": "🔧", "限制类": "⛔", "场景类": "💡", "异常类": "🚨"}

    for category, faqs in faq_by_category.items():
        icon = category_icons.get(category, "📌")
        st.markdown(f"### {icon} {category}")
        for i, faq in enumerate(faqs, 1):
            st.markdown(f"""
            <div class="faq-item">
                <div class="faq-question">Q{i}: {faq.question}</div>
                <div class="faq-answer">A: {faq.answer}</div>
            </div>
            """, unsafe_allow_html=True)


def render_export_page():
    """渲染导出下载页面"""
    material = st.session_state.material
    if not material:
        st.warning("请先生成培训材料")
        return

    st.title("📤 导出下载")

    output_dir = st.session_state.get("output_dir", tempfile.mkdtemp())

    # 显示模板状态
    if st.session_state.template_config:
        st.info(f"📊 使用模板: {st.session_state.template_config.template_name}")
    else:
        st.info("📊 使用默认样式生成 PPT")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 PPT 演示文稿")
        st.markdown("包含功能讲解、业务价值、操作步骤")
        ppt_path = f"{output_dir}/training_slides.pptx"
        if os.path.exists(ppt_path):
            with open(ppt_path, "rb") as f:
                st.download_button(
                    label="📥 下载 PPT",
                    data=f.read(),
                    file_name=f"training_{material.version}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
        else:
            if st.button("生成 PPT", use_container_width=True):
                with st.spinner("正在生成 PPT..."):
                    try:
                        # 使用模板配置
                        ppt_gen = PPTGenerator(template_config=st.session_state.template_config)
                        ppt_gen.generate(material, ppt_path)
                        st.success("PPT 生成成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {e}")

    with col2:
        st.markdown("### 🎬 视频脚本")
        st.markdown("演示视频旁白脚本（Markdown）")
        script_path = f"{output_dir}/video_script.md"
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 下载脚本",
                    data=f.read(),
                    file_name=f"video_script_{material.version}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        else:
            if st.button("生成脚本", use_container_width=True):
                with st.spinner("正在生成脚本..."):
                    try:
                        VideoScriptGenerator().generate(material, script_path)
                        st.success("脚本生成成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {e}")

    with col3:
        st.markdown("### ❓ FAQ 文档")
        st.markdown("常见问题文档（Markdown）")
        faq_path = f"{output_dir}/faq.md"
        if os.path.exists(faq_path):
            with open(faq_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 下载 FAQ",
                    data=f.read(),
                    file_name=f"faq_{material.version}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        else:
            if st.button("生成 FAQ", use_container_width=True):
                with st.spinner("正在生成 FAQ..."):
                    try:
                        FAQGenerator().generate(material, faq_path)
                        st.success("FAQ 生成成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {e}")

    # 一键全部重新生成
    st.divider()
    if st.button("🔄 重新生成全部文档", type="primary", use_container_width=True):
        with st.spinner("正在重新生成所有文档..."):
            try:
                # 使用模板配置生成 PPT
                ppt_gen = PPTGenerator(template_config=st.session_state.template_config)
                ppt_gen.generate(material, f"{output_dir}/training_slides.pptx")
                VideoScriptGenerator().generate(material, f"{output_dir}/video_script.md")
                FAQGenerator().generate(material, f"{output_dir}/faq.md")
                st.success("✅ 所有文档重新生成成功！")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 生成失败: {e}")


def main():
    """主入口"""
    init_session_state()
    render_sidebar()

    step = st.session_state.step
    if step == "config":
        render_config_page()
    elif step == "preview":
        render_preview_page()
    elif step == "value":
        render_value_page()
    elif step == "flow":
        render_flow_page()
    elif step == "faq":
        render_faq_page()
    elif step == "export":
        render_export_page()
    else:
        render_config_page()


if __name__ == "__main__":
    main()
