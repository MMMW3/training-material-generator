"""
培训材料生成器 - 核心数据模型
定义功能信息、业务价值、操作流程、FAQ等数据结构
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class FeaturePriority(str, Enum):
    P0 = "P0-核心功能"
    P1 = "P1-重要功能"
    P2 = "P2-辅助功能"
    TECHNICAL = "TECH-技术优化"


@dataclass
class JiraStoryInfo:
    """Jira Story 提取的结构化信息"""
    key: str
    summary: str
    description: str
    story_type: str  # Story, Sub-task, Bug
    priority: str
    status: str
    labels: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    user_story: Optional[str] = None  # "As a... I want... So that..."
    linked_issues: list[str] = field(default_factory=list)


@dataclass
class GitHubPRInfo:
    """GitHub PR 提取的结构化信息"""
    number: int
    title: str
    description: str
    state: str
    base_branch: str
    head_branch: str
    files_changed: list[str] = field(default_factory=list)
    commits: list[dict] = field(default_factory=list)  # [{message, sha, author}]
    labels: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)


@dataclass
class CodeChangeInfo:
    """代码变更分析结果"""
    file_path: str
    change_type: str  # added, modified, deleted
    category: str  # frontend, backend, config, database, test
    details: dict = field(default_factory=dict)
    # category=frontend: {components: [], routes: [], forms: []}
    # category=backend: {apis: [], services: [], permissions: []}
    # category=config: {config_keys: [], env_vars: []}


@dataclass
class FeatureInfo:
    """融合后的功能信息"""
    name: str
    description: str
    priority: FeaturePriority
    jira_stories: list[JiraStoryInfo] = field(default_factory=list)
    github_prs: list[GitHubPRInfo] = field(default_factory=list)
    code_changes: list[CodeChangeInfo] = field(default_factory=list)
    target_audience: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)


@dataclass
class BusinessValue:
    """业务价值分析结果"""
    problem_statement: str  # 解决什么问题
    value_proposition: str  # 核心价值主张
    before_scenario: str  # 使用前的痛点
    after_scenario: str  # 使用后的改善
    target_audience: list[str]  # 目标受众
    key_benefits: list[str]  # 关键收益


@dataclass
class OperationStep:
    """操作步骤"""
    step_number: int
    action: str  # 用户操作
    description: str  # 详细说明
    expected_result: str  # 预期结果
    screenshot_hint: str = ""  # 截图建议


@dataclass
class OperationFlow:
    """操作流程"""
    feature_name: str
    entry_point: str  # 功能入口
    steps: list[OperationStep] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # 注意事项
    related_features: list[str] = field(default_factory=list)


@dataclass
class FAQItem:
    """FAQ 条目"""
    question: str
    answer: str
    category: str  # 操作类, 限制类, 场景类, 异常类


@dataclass
class TrainingMaterial:
    """完整的培训材料"""
    version: str
    release_date: str
    features: list[FeatureInfo] = field(default_factory=list)
    business_values: dict[str, BusinessValue] = field(default_factory=dict)  # feature_name -> BusinessValue
    operation_flows: dict[str, OperationFlow] = field(default_factory=dict)  # feature_name -> OperationFlow
    faqs: list[FAQItem] = field(default_factory=list)
    summary: str = ""  # 整体更新概览


@dataclass
class PPTTemplateConfig:
    """PPT 模板配置"""
    template_path: str = ""  # 模板文件路径
    template_name: str = "默认模板"
    # 页面映射配置
    page_mappings: dict[str, int] = field(default_factory=dict)
    # 样式配置
    title_font_size: int = 36
    body_font_size: int = 18
    primary_color: str = "1F4E79"  # 主色
    accent_color: str = "ED7D31"   # 强调色
    # 占位符配置
    placeholders: dict[str, str] = field(default_factory=dict)
    # 是否启用模板
    enabled: bool = False


# 预定义的页面类型
class PageType(str, Enum):
    """PPT 页面类型"""
    COVER = "cover"              # 封面
    OVERVIEW = "overview"         # 更新概览
    FEATURE_TITLE = "feature_title"  # 功能标题页
    BUSINESS_VALUE = "business_value"  # 业务价值页
    OPERATION_FLOW = "operation_flow"  # 操作流程页
    ROLE_SUMMARY = "role_summary"  # 角色总结页
    FAQ = "faq"                  # FAQ 页
    END = "end"                  # 结束页
