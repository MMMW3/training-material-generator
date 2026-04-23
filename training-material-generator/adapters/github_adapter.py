"""
GitHub 数据适配器
从 GitHub API 提取 PR、Commit、文件变更信息
"""

import re
import logging
from typing import Optional

from models import GitHubPRInfo, CodeChangeInfo

logger = logging.getLogger(__name__)


class GitHubAdapter:
    """GitHub API 适配器"""

    def __init__(self, access_token: str):
        """
        初始化 GitHub 适配器

        Args:
            access_token: GitHub Personal Access Token
        """
        self.access_token = access_token
        self._github = None

    def _get_client(self):
        """懒加载 GitHub 客户端"""
        if self._github is None:
            try:
                from github import Github
                self._github = Github(self.access_token)
                logger.info("GitHub 客户端连接成功")
            except ImportError:
                raise ImportError("请安装 PyGithub 库: pip install PyGithub")
            except Exception as e:
                raise ConnectionError(f"GitHub 连接失败: {e}")
        return self._github

    def _categorize_file(self, file_path: str) -> str:
        """根据文件路径判断变更类别"""
        frontend_patterns = [
            r'\.(tsx?|jsx?|vue|svelte|css|scss|less)$',
            r'components/', r'pages/', r'screens/', r'views/',
            r'templates/', r'static/', r'public/', r'assets/',
        ]
        backend_patterns = [
            r'\.(py|java|go|rs|rb|php|cs)$',
            r'controllers/', r'services/', r'handlers/',
            r'repositories/', r'dao/', r'models/',
        ]
        config_patterns = [
            r'\.(yml|yaml|toml|ini|env|conf|cfg)$',
            r'dockerfile', r'makefile',
            r'\.github/', r'kubernetes/', r'k8s/',
        ]
        database_patterns = [
            r'\.(sql|graphql)$',
            r'migrations/', r'seeds/', r'schema/',
        ]
        test_patterns = [
            r'test[_/]', r'spec[_/]', r'__tests__/',
            r'_test\.', r'_spec\.', r'\.test\.', r'\.spec\.',
        ]

        path_lower = file_path.lower()
        for pattern in test_patterns:
            if re.search(pattern, path_lower):
                return "test"
        for pattern in frontend_patterns:
            if re.search(pattern, path_lower):
                return "frontend"
        for pattern in backend_patterns:
            if re.search(pattern, path_lower):
                return "backend"
        for pattern in config_patterns:
            if re.search(pattern, path_lower):
                return "config"
        for pattern in database_patterns:
            if re.search(pattern, path_lower):
                return "database"
        return "other"

    def _extract_pr_info(self, pull_request) -> GitHubPRInfo:
        """将 GitHub PR 转换为 GitHubPRInfo"""
        files_changed = []
        commits = []
        try:
            for file in pull_request.get_files():
                files_changed.append(file.filename)
            for commit in pull_request.get_commits():
                commits.append({
                    "message": commit.commit.message,
                    "sha": commit.sha,
                    "author": commit.commit.author.name if commit.commit.author else "Unknown",
                })
        except Exception as e:
            logger.warning(f"获取 PR #{pull_request.number} 详情失败: {e}")

        return GitHubPRInfo(
            number=pull_request.number,
            title=pull_request.title,
            description=pull_request.body or "",
            state=pull_request.state,
            base_branch=pull_request.base.ref,
            head_branch=pull_request.head.ref,
            files_changed=files_changed,
            commits=commits,
            labels=[label.name for label in pull_request.labels],
            reviewers=[reviewer.login for reviewer in pull_request.requested_reviewers],
        )

    def get_prs_by_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> list[GitHubPRInfo]:
        """
        获取指定分支的所有 PR

        Args:
            repo_name: 仓库全名，如 "owner/repo"
            branch_name: 功能分支名
            base_branch: 基础分支名

        Returns:
            GitHubPRInfo 列表
        """
        github = self._get_client()
        repo = github.get_repo(repo_name)
        prs = []

        try:
            pulls = repo.get_pulls(
                state="closed",
                base=base_branch,
                head=f"{repo.owner.login}:{branch_name}",
                sort="updated",
                direction="desc"
            )
            for pr in pulls:
                if pr.merged:
                    prs.append(self._extract_pr_info(pr))

            logger.info(f"从 {repo_name} 分支 {branch_name} 获取了 {len(prs)} 个已合并 PR")
            return prs
        except Exception as e:
            logger.error(f"获取 PR 失败: {e}")
            raise

    def get_prs_by_labels(self, repo_name: str, labels: list[str], state: str = "closed") -> list[GitHubPRInfo]:
        """
        通过标签获取 PR

        Args:
            repo_name: 仓库全名
            labels: 标签列表
            state: PR 状态

        Returns:
            GitHubPRInfo 列表
        """
        github = self._get_client()
        repo = github.get_repo(repo_name)
        prs = []

        try:
            pulls = repo.get_pulls(state=state, sort="updated", direction="desc")
            for pr in pulls:
                pr_labels = [label.name for label in pr.labels]
                if any(label in pr_labels for label in labels):
                    prs.append(self._extract_pr_info(pr))

            logger.info(f"从 {repo_name} 获取了 {len(prs)} 个匹配标签的 PR")
            return prs
        except Exception as e:
            logger.error(f"获取 PR 失败: {e}")
            raise

    def get_pr_by_number(self, repo_name: str, pr_number: int) -> Optional[GitHubPRInfo]:
        """通过 PR 编号获取 PR 信息"""
        github = self._get_client()
        repo = github.get_repo(repo_name)

        try:
            pr = repo.get_pull(pr_number)
            return self._extract_pr_info(pr)
        except Exception as e:
            logger.error(f"获取 PR #{pr_number} 失败: {e}")
            return None

    def get_file_changes(self, repo_name: str, pr_numbers: list[int]) -> list[CodeChangeInfo]:
        """
        获取 PR 中的文件变更并分类

        Args:
            repo_name: 仓库全名
            pr_numbers: PR 编号列表

        Returns:
            CodeChangeInfo 列表
        """
        github = self._get_client()
        repo = github.get_repo(repo_name)
        changes = []

        for pr_num in pr_numbers:
            try:
                pr = repo.get_pull(pr_num)
                for file in pr.get_files():
                    category = self._categorize_file(file.filename)
                    change_info = CodeChangeInfo(
                        file_path=file.filename,
                        change_type=file.status,  # added, modified, removed
                        category=category,
                        details={
                            "additions": file.additions,
                            "deletions": file.deletions,
                            "patch": file.patch[:2000] if file.patch else "",  # 限制大小
                        }
                    )
                    changes.append(change_info)
            except Exception as e:
                logger.warning(f"获取 PR #{pr_num} 文件变更失败: {e}")

        logger.info(f"获取了 {len(changes)} 个文件变更")
        return changes

    def get_file_content(self, repo_name: str, file_path: str, ref: str = "main") -> Optional[str]:
        """获取仓库中指定文件的内容"""
        github = self._get_client()
        repo = github.get_repo(repo_name)

        try:
            file = repo.get_contents(file_path, ref=ref)
            if isinstance(file, list):
                return None
            return file.decoded_content.decode("utf-8")
        except Exception as e:
            logger.warning(f"获取文件 {file_path} 失败: {e}")
            return None

    def test_connection(self) -> bool:
        """测试 GitHub 连接"""
        try:
            github = self._get_client()
            user = github.get_user()
            logger.info(f"GitHub 连接测试成功，用户: {user.login}")
            return True
        except Exception as e:
            logger.error(f"GitHub 连接测试失败: {e}")
            return False
