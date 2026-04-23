"""
核心编排器
串联所有模块：数据提取 → AI分析 → 文档生成
"""

import logging
from typing import Optional
from datetime import datetime

from models import (
    TrainingMaterial, FeatureInfo, FeaturePriority,
    JiraStoryInfo, GitHubPRInfo, CodeChangeInfo,
)
from adapters.jira_adapter import JiraAdapter
from adapters.github_adapter import GitHubAdapter
from analyzers.code_analyzer import CodeAnalyzer
from analyzers.ai_analyzer import AIAnalyzer
from generators.ppt_generator import PPTGenerator
from generators.video_script_generator import VideoScriptGenerator
from generators.faq_generator import FAQGenerator

logger = logging.getLogger(__name__)


class TrainingMaterialOrchestrator:
    """培训材料生成编排器"""

    def __init__(
        self,
        jira_adapter: Optional[JiraAdapter] = None,
        github_adapter: Optional[GitHubAdapter] = None,
        ai_analyzer: Optional[AIAnalyzer] = None,
    ):
        self.jira_adapter = jira_adapter
        self.github_adapter = github_adapter
        self.ai_analyzer = ai_analyzer
        self.code_analyzer = CodeAnalyzer()
        self.ppt_generator = PPTGenerator()
        self.video_script_generator = VideoScriptGenerator()
        self.faq_generator = FAQGenerator()

    def generate_from_jira_epic(
        self,
        epic_key: str,
        github_repo: Optional[str] = None,
        github_pr_numbers: Optional[list[int]] = None,
        version: str = "",
        release_date: str = "",
        output_dir: str = "./output",
    ) -> TrainingMaterial:
        """
        从 Jira Epic 生成培训材料

        Args:
            epic_key: Jira Epic Key
            github_repo: GitHub 仓库全名（可选）
            github_pr_numbers: GitHub PR 编号列表（可选）
            version: 版本号
            release_date: 发布日期
            output_dir: 输出目录

        Returns:
            TrainingMaterial
        """
        logger.info(f"开始从 Epic {epic_key} 生成培训材料...")

        # Step 1: 提取 Jira 信息
        jira_stories = []
        if self.jira_adapter:
            logger.info("正在从 Jira 提取信息...")
            jira_stories = self.jira_adapter.get_epic_stories(epic_key)
            logger.info(f"提取了 {len(jira_stories)} 个 Jira Issue")
        else:
            logger.warning("Jira 适配器未配置，跳过 Jira 信息提取")

        # Step 2: 提取 GitHub 信息
        github_prs = []
        code_changes = []
        if self.github_adapter and github_repo:
            logger.info("正在从 GitHub 提取信息...")
            if github_pr_numbers:
                for pr_num in github_pr_numbers:
                    pr_info = self.github_adapter.get_pr_by_number(github_repo, pr_num)
                    if pr_info:
                        github_prs.append(pr_info)
                code_changes = self.github_adapter.get_file_changes(github_repo, github_pr_numbers)
            logger.info(f"提取了 {len(github_prs)} 个 PR, {len(code_changes)} 个文件变更")
        else:
            logger.warning("GitHub 适配器未配置或仓库未指定，跳过 GitHub 信息提取")

        # Step 3: 构建功能信息
        features = self._build_features(jira_stories, github_prs, code_changes)
        logger.info(f"识别了 {len(features)} 个功能")

        # Step 4: AI 分析
        material = TrainingMaterial(
            version=version or datetime.now().strftime("%Y-%m-%d"),
            release_date=release_date or datetime.now().strftime("%Y年%m月%d日"),
            features=features,
        )

        if self.ai_analyzer:
            logger.info("正在进行 AI 分析...")
            # 生成整体概览
            material.summary = self.ai_analyzer.generate_summary(features)

            # 逐功能分析
            for feature in features:
                # 业务价值分析
                bv = self.ai_analyzer.analyze_business_value(feature)
                material.business_values[feature.name] = bv

                # 代码分析 → 操作流程
                frontend_analysis = self.code_analyzer.analyze_frontend_changes(feature.code_changes)
                backend_analysis = self.code_analyzer.analyze_backend_changes(feature.code_changes)
                code_flow = self.code_analyzer.build_operation_flow(
                    feature.name, frontend_analysis, backend_analysis
                )

                # AI 优化操作流程
                refined_flow = self.ai_analyzer.refine_operation_flow(feature, code_flow)
                material.operation_flows[feature.name] = refined_flow

                # 生成 FAQ
                faqs = self.ai_analyzer.generate_faqs(feature, bv)
                material.faqs.extend(faqs)
        else:
            logger.warning("AI 分析器未配置，跳过智能分析")
            material.summary = f"本次更新包含 {len(features)} 个功能变更。"

        # Step 5: 生成文档
        logger.info("正在生成培训文档...")
        self.ppt_generator.generate(material, f"{output_dir}/training_slides.pptx")
        self.video_script_generator.generate(material, f"{output_dir}/video_script.md")
        self.faq_generator.generate(material, f"{output_dir}/faq.md")

        logger.info("培训材料生成完成！")
        return material

    def generate_from_github_only(
        self,
        github_repo: str,
        pr_numbers: list[int],
        version: str = "",
        release_date: str = "",
        output_dir: str = "./output",
    ) -> TrainingMaterial:
        """
        仅从 GitHub PR 生成培训材料（无 Jira 场景）

        Args:
            github_repo: GitHub 仓库全名
            pr_numbers: PR 编号列表
            version: 版本号
            release_date: 发布日期
            output_dir: 输出目录

        Returns:
            TrainingMaterial
        """
        if not self.github_adapter:
            raise ValueError("需要配置 GitHub 适配器")

        logger.info(f"开始从 GitHub PR 生成培训材料...")

        # 提取 GitHub 信息
        github_prs = []
        for pr_num in pr_numbers:
            pr_info = self.github_adapter.get_pr_by_number(github_repo, pr_num)
            if pr_info:
                github_prs.append(pr_info)

        code_changes = self.github_adapter.get_file_changes(github_repo, pr_numbers)

        # 构建 Feature（每个 PR 对应一个功能）
        features = []
        for pr in github_prs:
            related_changes = [c for c in code_changes if any(
                f in c.file_path for f in pr.files_changed
            )]
            features.append(FeatureInfo(
                name=pr.title,
                description=pr.description[:200] if pr.description else pr.title,
                priority=FeaturePriority.P1,
                github_prs=[pr],
                code_changes=related_changes,
            ))

        # 构建培训材料
        material = TrainingMaterial(
            version=version or datetime.now().strftime("%Y-%m-%d"),
            release_date=release_date or datetime.now().strftime("%Y年%m月%d日"),
            features=features,
        )

        # AI 分析
        if self.ai_analyzer:
            material.summary = self.ai_analyzer.generate_summary(features)
            for feature in features:
                bv = self.ai_analyzer.analyze_business_value(feature)
                material.business_values[feature.name] = bv

                frontend_analysis = self.code_analyzer.analyze_frontend_changes(feature.code_changes)
                backend_analysis = self.code_analyzer.analyze_backend_changes(feature.code_changes)
                code_flow = self.code_analyzer.build_operation_flow(
                    feature.name, frontend_analysis, backend_analysis
                )
                refined_flow = self.ai_analyzer.refine_operation_flow(feature, code_flow)
                material.operation_flows[feature.name] = refined_flow

                faqs = self.ai_analyzer.generate_faqs(feature, bv)
                material.faqs.extend(faqs)
        else:
            material.summary = f"本次更新包含 {len(features)} 个功能变更。"

        # 生成文档
        self.ppt_generator.generate(material, f"{output_dir}/training_slides.pptx")
        self.video_script_generator.generate(material, f"{output_dir}/video_script.md")
        self.faq_generator.generate(material, f"{output_dir}/faq.md")

        logger.info("培训材料生成完成！")
        return material

    def _build_features(
        self,
        jira_stories: list[JiraStoryInfo],
        github_prs: list[GitHubPRInfo],
        code_changes: list[CodeChangeInfo],
    ) -> list[FeatureInfo]:
        """
        将 Jira Stories 和 GitHub PRs 融合为 Feature 列表

        策略：
        1. 以 Jira Story 为主要功能单元
        2. 通过分支名/标签匹配关联 GitHub PR
        3. 过滤掉纯技术优化
        """
        features = []

        # 过滤用户可感知的功能
        user_facing_stories = [
            s for s in jira_stories
            if s.story_type in ("Story", "Sub-task", "New Feature", "改进")
            and not self._is_technical_only(s)
        ]

        for story in user_facing_stories:
            # 匹配关联的 PR
            related_prs = self._match_prs_to_story(story, github_prs)
            related_changes = self._match_changes_to_story(story, code_changes, related_prs)

            # 判断优先级
            priority = self._determine_priority(story)

            feature = FeatureInfo(
                name=story.summary,
                description=self._extract_user_description(story),
                priority=priority,
                jira_stories=[story],
                github_prs=related_prs,
                code_changes=related_changes,
                target_audience=self._extract_audience(story),
                affected_modules=self._extract_modules(related_changes),
            )
            features.append(feature)

        # 补充没有关联 Jira 的 PR
        matched_pr_numbers = {pr.number for f in features for pr in f.github_prs}
        for pr in github_prs:
            if pr.number not in matched_pr_numbers and not self._is_pr_technical_only(pr):
                related_changes = [c for c in code_changes if any(
                    f in c.file_path for f in pr.files_changed
                )]
                features.append(FeatureInfo(
                    name=pr.title,
                    description=pr.description[:200] if pr.description else pr.title,
                    priority=FeaturePriority.P2,
                    github_prs=[pr],
                    code_changes=related_changes,
                ))

        return features

    def _is_technical_only(self, story: JiraStoryInfo) -> bool:
        """判断是否为纯技术优化"""
        tech_keywords = [
            "重构", "refactor", "性能优化", "performance",
            "代码清理", "code cleanup", "依赖升级", "dependency",
            "CI/CD", "测试", "test", "bug fix", "修复",
            "技术债务", "tech debt",
        ]
        text = (story.summary + " " + story.description).lower()
        return any(kw in text for kw in tech_keywords)

    def _is_pr_technical_only(self, pr: GitHubPRInfo) -> bool:
        """判断 PR 是否为纯技术变更"""
        tech_keywords = ["refactor", "chore", "deps", "ci", "test", "lint", "format"]
        text = (pr.title + " " + pr.description).lower()
        labels_lower = [l.lower() for l in pr.labels]
        return any(kw in text for kw in tech_keywords) or any(
            kw in labels_lower for kw in tech_keywords
        )

    def _match_prs_to_story(self, story: JiraStoryInfo, prs: list[GitHubPRInfo]) -> list[GitHubPRInfo]:
        """通过分支名/标签/标题匹配 PR 到 Story"""
        story_key = story.key.lower()
        story_words = story.summary.lower().split()

        matched = []
        for pr in prs:
            # 通过 Jira Key 匹配
            if story_key in pr.head_branch.lower() or story_key in pr.title.lower():
                matched.append(pr)
                continue
            # 通过标签匹配
            if story_key in [l.lower() for l in pr.labels]:
                matched.append(pr)
                continue
            # 通过关键词匹配
            pr_words = pr.title.lower().split()
            if len(set(story_words) & set(pr_words)) >= 2:
                matched.append(pr)

        return matched

    def _match_changes_to_story(
        self,
        story: JiraStoryInfo,
        changes: list[CodeChangeInfo],
        matched_prs: list[GitHubPRInfo],
    ) -> list[CodeChangeInfo]:
        """匹配代码变更到 Story"""
        if not matched_prs:
            return []

        pr_files = set()
        for pr in matched_prs:
            pr_files.update(pr.files_changed)

        return [c for c in changes if c.file_path in pr_files]

    def _determine_priority(self, story: JiraStoryInfo) -> FeaturePriority:
        """根据 Jira 信息判断功能优先级"""
        priority_map = {
            "highest": FeaturePriority.P0,
            "high": FeaturePriority.P0,
            "medium": FeaturePriority.P1,
            "low": FeaturePriority.P2,
            "lowest": FeaturePriority.P2,
        }
        return priority_map.get(story.priority.lower(), FeaturePriority.P1)

    def _extract_user_description(self, story: JiraStoryInfo) -> str:
        """提取用户友好的功能描述"""
        if story.user_story:
            return story.user_story
        # 从描述中提取第一段非技术文字
        lines = story.description.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith(("#", "*", "-", "|", "```", "@")):
                return line[:200]
        return story.summary

    def _extract_audience(self, story: JiraStoryInfo) -> list[str]:
        """从 Story 中提取目标受众"""
        audience_keywords = {
            "管理员": ["admin", "管理员", "管理后台"],
            "运营人员": ["运营", "operation", "marketing"],
            "财务人员": ["财务", "finance", "billing"],
            "普通用户": ["用户", "user", "member"],
            "审批人": ["审批", "approve", "reviewer"],
        }
        text = (story.summary + " " + story.description).lower()
        audiences = []
        for role, keywords in audience_keywords.items():
            if any(kw in text for kw in keywords):
                audiences.append(role)
        return audiences or ["全体用户"]

    def _extract_modules(self, changes: list[CodeChangeInfo]) -> list[str]:
        """从代码变更中提取涉及的模块"""
        modules = set()
        for change in changes:
            parts = change.file_path.split("/")
            if len(parts) >= 2:
                modules.add(parts[0] + "/" + parts[1])
            elif len(parts) >= 1:
                modules.add(parts[0])
        return list(modules)
