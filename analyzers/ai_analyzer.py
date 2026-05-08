"""
AI 分析引擎
使用 LLM 将技术信息翻译为业务价值、操作流程和 FAQ
支持 OpenAI API 及兼容接口
"""

import json
import logging
from typing import Optional

from models import (
    FeatureInfo, BusinessValue, OperationFlow, OperationStep,
    FAQItem, JiraStoryInfo, GitHubPRInfo, CodeChangeInfo,
)

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析引擎 - 业务价值翻译器"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o"):
        """
        初始化 AI 分析引擎

        Args:
            api_key: OpenAI API Key
            base_url: API 基础 URL（支持兼容接口）
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = None

    def _get_client(self):
        """懒加载 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                logger.info(f"AI 客户端初始化成功，模型: {self.model}")
            except ImportError:
                raise ImportError("请安装 openai 库: pip install openai")
        return self._client

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """调用 LLM Chat API"""
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI 调用失败: {e}")
            raise

    def analyze_business_value(self, feature: FeatureInfo) -> BusinessValue:
        """
        分析功能的业务价值

        将技术描述翻译为用户可理解的业务价值
        """
        # 构建上下文
        context = self._build_feature_context(feature)

        system_prompt = """你是一位资深的 toB 产品经理，擅长将技术实现翻译为用户可理解的业务价值。

你的任务是根据提供的技术信息（Jira描述、代码变更等），提炼出用户层面的业务价值。

请严格按以下 JSON 格式输出，不要包含其他文字：
{
    "problem_statement": "这个功能解决了什么业务问题？（用用户视角描述痛点）",
    "value_proposition": "用一句话概括核心价值，格式：通过[功能]，用户可以[动作]，从而[业务收益]",
    "before_scenario": "没有这个功能时，用户是怎么做的？有什么痛点？",
    "after_scenario": "有了这个功能后，用户的体验如何改善？",
    "target_audience": ["角色1", "角色2"],
    "key_benefits": ["收益1", "收益2", "收益3"]
}

要求：
1. 使用业务语言，避免技术术语
2. 从用户视角出发，强调"对我有什么好处"
3. before/after 对比要具体、有画面感
4. 目标受众要明确到具体岗位角色"""

        user_prompt = f"""请分析以下功能信息的业务价值：

功能名称：{feature.name}
功能描述：{feature.description}

Jira 信息：
{self._format_jira_for_prompt(feature.jira_stories)}

GitHub PR 信息：
{self._format_github_for_prompt(feature.github_prs)}

代码变更摘要：
{self._format_code_changes_for_prompt(feature.code_changes)}"""

        response = self._chat(system_prompt, user_prompt, temperature=0.7)

        try:
            # 提取 JSON
            json_match = response
            if "```json" in response:
                json_match = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_match = response.split("```")[1].split("```")[0]

            data = json.loads(json_match)
            return BusinessValue(
                problem_statement=data.get("problem_statement", ""),
                value_proposition=data.get("value_proposition", ""),
                before_scenario=data.get("before_scenario", ""),
                after_scenario=data.get("after_scenario", ""),
                target_audience=data.get("target_audience", []),
                key_benefits=data.get("key_benefits", []),
            )
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"解析 AI 响应失败: {e}, 使用原始响应")
            return BusinessValue(
                problem_statement=response,
                value_proposition=response[:100],
                before_scenario="",
                after_scenario="",
                target_audience=[],
                key_benefits=[],
            )

    def generate_faqs(self, feature: FeatureInfo, business_value: BusinessValue) -> list[FAQItem]:
        """
        生成 FAQ

        基于功能信息和业务价值，预判用户可能的问题
        """
        context = self._build_feature_context(feature)

        system_prompt = """你是一位资深的 toB 产品经理，正在为新功能编写用户 FAQ。

请根据提供的技术信息和业务价值，预判用户最可能提出的问题，并给出清晰的回答。

请严格按以下 JSON 格式输出：
[
    {
        "question": "用户可能提出的问题",
        "answer": "简洁清晰的回答",
        "category": "分类（操作类/限制类/场景类/异常类）"
    }
]

要求：
1. 生成 5-8 个 FAQ
2. 问题要站在用户视角，使用业务语言
3. 回答要具体、可操作，避免模糊表述
4. 覆盖以下维度：
   - 基本操作类：怎么用？入口在哪里？
   - 限制条件类：有什么限制？为什么不能XXX？
   - 场景适用类：什么情况下用？和XXX有什么区别？
   - 异常处理类：操作失败怎么办？XXX提示是什么意思？"""

        user_prompt = f"""请为以下功能生成 FAQ：

功能名称：{feature.name}
功能描述：{feature.description}

业务价值：
- 解决的问题：{business_value.problem_statement}
- 核心价值：{business_value.value_proposition}
- 使用前：{business_value.before_scenario}
- 使用后：{business_value.after_scenario}
- 目标受众：{', '.join(business_value.target_audience)}

技术细节：
{context}"""

        response = self._chat(system_prompt, user_prompt, temperature=0.8)

        try:
            json_match = response
            if "```json" in response:
                json_match = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_match = response.split("```")[1].split("```")[0]

            faqs_data = json.loads(json_match)
            return [
                FAQItem(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    category=item.get("category", "操作类"),
                )
                for item in faqs_data
            ]
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"解析 FAQ 响应失败: {e}")
            return []

    def refine_operation_flow(self, feature: FeatureInfo, code_flow: OperationFlow) -> OperationFlow:
        """
        用 AI 优化代码分析器生成的操作流程

        将技术化的步骤描述翻译为用户友好的操作指引
        """
        steps_text = "\n".join([
            f"步骤{s.step_number}: {s.action} - {s.description}"
            for s in code_flow.steps
        ])

        system_prompt = """你是一位资深的 toB 产品经理，正在编写用户操作指引。

请将以下技术化的操作步骤翻译为用户友好的操作指引。

请严格按以下 JSON 格式输出：
{
    "entry_point": "功能入口的友好描述",
    "steps": [
        {
            "step_number": 1,
            "action": "用户操作（动词开头，如：点击、填写、选择）",
            "description": "详细操作说明（包含在哪里操作、操作什么）",
            "expected_result": "操作后预期看到什么结果",
            "screenshot_hint": "建议截图的内容描述"
        }
    ],
    "notes": ["注意事项1", "注意事项2"]
}

要求：
1. 使用用户语言，避免技术术语
2. 每个步骤要具体到界面元素（按钮、输入框、菜单等）
3. 预期结果要明确、可验证
4. 注意事项要包含常见误区和限制条件"""

        user_prompt = f"""请优化以下操作流程：

功能名称：{feature.name}
功能描述：{feature.description}

当前操作步骤：
{steps_text}

注意事项：{', '.join(code_flow.notes)}"""

        response = self._chat(system_prompt, user_prompt, temperature=0.5)

        try:
            json_match = response
            if "```json" in response:
                json_match = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_match = response.split("```")[1].split("```")[0]

            data = json.loads(json_match)
            steps = [
                OperationStep(
                    step_number=s.get("step_number", i + 1),
                    action=s.get("action", ""),
                    description=s.get("description", ""),
                    expected_result=s.get("expected_result", ""),
                    screenshot_hint=s.get("screenshot_hint", ""),
                )
                for i, s in enumerate(data.get("steps", []))
            ]
            return OperationFlow(
                feature_name=feature.name,
                entry_point=data.get("entry_point", code_flow.entry_point),
                steps=steps,
                notes=data.get("notes", code_flow.notes),
                related_features=code_flow.related_features,
            )
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"解析操作流程响应失败: {e}")
            return code_flow

    def generate_summary(self, features: list[FeatureInfo]) -> str:
        """生成整体更新概览"""
        feature_list = "\n".join([
            f"- {f.name}（{f.priority.value}）：{f.description}"
            for f in features
        ])

        system_prompt = """你是一位资深的 toB 产品经理，请为一组新功能生成简洁的更新概览。

要求：
1. 用 2-3 句话概括本次更新的核心主题
2. 突出对用户的价值
3. 使用业务语言，避免技术术语"""

        user_prompt = f"""请为以下功能列表生成更新概览：

{feature_list}"""

        return self._chat(system_prompt, user_prompt, temperature=0.7)

    def _build_feature_context(self, feature: FeatureInfo) -> str:
        """构建功能的完整上下文"""
        parts = []
        parts.append(self._format_jira_for_prompt(feature.jira_stories))
        parts.append(self._format_github_for_prompt(feature.github_prs))
        parts.append(self._format_code_changes_for_prompt(feature.code_changes))
        return "\n\n".join(parts)

    def _format_jira_for_prompt(self, stories: list[JiraStoryInfo]) -> str:
        """格式化 Jira 信息用于 Prompt"""
        if not stories:
            return "无 Jira 信息"
        lines = []
        for s in stories:
            lines.append(f"[{s.key}] {s.summary}（{s.story_type}, {s.priority}）")
            if s.user_story:
                lines.append(f"  用户故事：{s.user_story}")
            if s.acceptance_criteria:
                lines.append(f"  验收标准：")
                for ac in s.acceptance_criteria:
                    lines.append(f"    - {ac}")
            if s.description:
                desc = s.description[:500]
                lines.append(f"  描述：{desc}")
        return "\n".join(lines)

    def _format_github_for_prompt(self, prs: list[GitHubPRInfo]) -> str:
        """格式化 GitHub PR 信息用于 Prompt"""
        if not prs:
            return "无 GitHub PR 信息"
        lines = []
        for pr in prs:
            lines.append(f"[PR #{pr.number}] {pr.title}")
            if pr.description:
                lines.append(f"  描述：{pr.description[:300]}")
            lines.append(f"  变更文件：{', '.join(pr.files_changed[:10])}")
            if pr.commits:
                for c in pr.commits[:3]:
                    lines.append(f"  提交：{c['message'][:100]}")
        return "\n".join(lines)

    def _format_code_changes_for_prompt(self, changes: list[CodeChangeInfo]) -> str:
        """格式化代码变更信息用于 Prompt"""
        if not changes:
            return "无代码变更信息"
        lines = []
        for c in changes:
            lines.append(f"[{c.change_type}] {c.file_path}（{c.category}）")
        return "\n".join(lines)
