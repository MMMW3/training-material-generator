"""
Jira Cloud 数据适配器
从 Jira Cloud API 提取 Epic/Story/Sub-task 信息
"""

import re
import logging
from typing import Optional

from models import JiraStoryInfo

logger = logging.getLogger(__name__)


class JiraAdapter:
    """Jira Cloud API 适配器"""

    def __init__(self, email: str, api_token: str, server_url: str = "https://your-domain.atlassian.net"):
        """
        初始化 Jira 适配器

        Args:
            email: Jira 账号邮箱
            api_token: Jira API Token (从 https://id.atlassian.com/manage-profile/security/api-tokens 获取)
            server_url: Jira 服务器地址
        """
        self.email = email
        self.api_token = api_token
        self.server_url = server_url.rstrip("/")
        self._jira = None

    def _get_client(self):
        """懒加载 Jira 客户端"""
        if self._jira is None:
            try:
                from jira import JIRA
                self._jira = JIRA(
                    server=self.server_url,
                    basic_auth=(self.email, self.api_token)
                )
                logger.info("Jira 客户端连接成功")
            except ImportError:
                raise ImportError(
                    "请安装 jira 库: pip install jira"
                )
            except Exception as e:
                raise ConnectionError(f"Jira 连接失败: {e}")
        return self._jira

    def _parse_acceptance_criteria(self, description: str) -> list[str]:
        """从描述中提取验收标准"""
        ac_patterns = [
            r'(?:Acceptance Criteria|AC|验收标准)[:\s]*\n(.*?)(?:\n\n|\n#|\Z)',
            r'(?:Given|When|Then).*',
        ]
        criteria = []
        for pattern in ac_patterns:
            matches = re.findall(pattern, description, re.DOTALL | re.IGNORECASE)
            for match in matches:
                items = re.findall(r'[-*]\s*(.+)', match)
                criteria.extend([item.strip() for item in items if item.strip()])
        return criteria

    def _parse_user_story(self, description: str) -> Optional[str]:
        """从描述中提取用户故事"""
        patterns = [
            r'(?:As a|作为)\s*.+?(?:I want|我想要|我需要).+?(?:So that|以便|从而).+',
            r'(?:As a|作为)\s*.+?(?:I can|我可以).+',
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _extract_story_info(self, issue) -> JiraStoryInfo:
        """将 Jira Issue 转换为 JiraStoryInfo"""
        description = issue.fields.description or ""
        comments = []
        try:
            for comment in issue.fields.comment.comments:
                comments.append(f"[{comment.author.displayName}]: {comment.body}")
        except Exception:
            pass

        return JiraStoryInfo(
            key=issue.key,
            summary=issue.fields.summary,
            description=description,
            story_type=issue.fields.issuetype.name,
            priority=issue.fields.priority.name if issue.fields.priority else "Unknown",
            status=issue.fields.status.name,
            labels=list(issue.fields.labels) if issue.fields.labels else [],
            acceptance_criteria=self._parse_acceptance_criteria(description),
            comments=comments,
            user_story=self._parse_user_story(description),
            linked_issues=[]
        )

    def get_epic_stories(self, epic_key: str) -> list[JiraStoryInfo]:
        """
        获取 Epic 下的所有 Story 和 Sub-task

        Args:
            epic_key: Epic 的 Issue Key，如 "PROJ-123"

        Returns:
            JiraStoryInfo 列表
        """
        jira = self._get_client()
        stories = []

        try:
            # 获取 Epic 本身的信息
            epic_issue = jira.issue(epic_key)
            stories.append(self._extract_story_info(epic_issue))

            # 查询 Epic 下的所有 Issue
            jql = f"'Epic Link' = {epic_key} OR 'Epic' = {epic_key} ORDER BY status ASC, priority DESC"
            jql_issues = jira.search_issues(jql, maxResults=100)

            for issue in jql_issues:
                if issue.key != epic_key:
                    story_info = self._extract_story_info(issue)
                    # 获取关联 Issue
                    try:
                        for link in issue.fields.issuelinks:
                            if hasattr(link, 'outwardIssue'):
                                story_info.linked_issues.append(link.outwardIssue.key)
                            elif hasattr(link, 'inwardIssue'):
                                story_info.linked_issues.append(link.inwardIssue.key)
                    except Exception:
                        pass
                    stories.append(story_info)

            logger.info(f"从 Epic {epic_key} 提取了 {len(stories)} 个 Issue")
            return stories

        except Exception as e:
            logger.error(f"获取 Epic {epic_key} 失败: {e}")
            raise

    def get_stories_by_keys(self, keys: list[str]) -> list[JiraStoryInfo]:
        """
        通过 Issue Key 列表获取 Story 信息

        Args:
            keys: Issue Key 列表，如 ["PROJ-123", "PROJ-124"]

        Returns:
            JiraStoryInfo 列表
        """
        jira = self._get_client()
        stories = []

        for key in keys:
            try:
                issue = jira.issue(key)
                stories.append(self._extract_story_info(issue))
            except Exception as e:
                logger.warning(f"获取 Issue {key} 失败: {e}")

        return stories

    def test_connection(self) -> bool:
        """测试 Jira 连接"""
        try:
            jira = self._get_client()
            jira.myself()
            logger.info("Jira 连接测试成功")
            return True
        except Exception as e:
            logger.error(f"Jira 连接测试失败: {e}")
            return False
