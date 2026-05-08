"""
代码分析器
分析代码变更，还原用户操作流程
"""

import re
import logging
from typing import Optional

from models import CodeChangeInfo, OperationStep, OperationFlow

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """代码变更分析器"""

    def __init__(self):
        # 前端框架特征
        self.framework_patterns = {
            "react": {
                "component": r'(?:function|const|class)\s+(\w+)(?:\s*=\s*(?:\(\)|\([^)]*\)))?\s*(?:=>|extends\s+Component|extends\s+React)',
                "route": r'(?:path|Route)\s*[=:]\s*["\']([^"\']+)["\']',
                "form_field": r'(?:name|fieldName|field)\s*[=:]\s*["\']([^"\']+)["\']',
                "button_action": r'(?:onClick|onSubmit|onPress)\s*[=:]\s*[{(]?\s*(\w+)',
                "api_call": r'(?:axios|fetch|useQuery|useMutation|api)\.\w+\(["\']([^"\']+)["\']',
                "permission": r'(?:permission|role|auth|can)\s*[=:]\s*["\']([^"\']+)["\']',
            },
            "vue": {
                "component": r'(?:export\s+default\s+)?(?:defineComponent|createApp)\s*\(',
                "route": r'(?:path|Route)\s*[=:]\s*["\']([^"\']+)["\']',
                "form_field": r'(?:v-model|name|prop)\s*[=:]\s*["\']([^"\']+)["\']',
                "button_action": r'@(?:click|submit)\s*[=:]\s*["\']([^"\']+)["\']',
                "api_call": r'(?:axios|fetch|this\.\$http|api)\.\w+\(["\']([^"\']+)["\']',
                "permission": r'v-(?:if|show)\s*=\s*["\']([^"\']*(?:permission|role|auth|can)[^"\']*)["\']',
            },
            "general": {
                "api_route": r'(?:@(?:Get|Post|Put|Delete|Patch|RequestMapping))\s*\(\s*["\']([^"\']+)["\']',
                "permission_annotation": r'@(?:PreAuthorize|RequiresPermissions|Secured)\s*\(\s*["\']([^"\']+)["\']',
                "validation": r'(?:@NotNull|@NotBlank|@Size|@Pattern|@Valid|required)\s*[:(]',
                "event": r'(?:emit|publish|dispatch|EventBus)\s*\(\s*["\']([^"\']+)["\']',
            }
        }

    def analyze_frontend_changes(self, code_changes: list[CodeChangeInfo]) -> dict:
        """
        分析前端代码变更，提取 UI 交互信息

        Returns:
            {
                "new_pages": [{"name": "", "route": ""}],
                "new_components": [{"name": "", "purpose": ""}],
                "form_fields": [{"field": "", "type": ""}],
                "actions": [{"name": "", "type": ""}],
                "api_calls": [{"endpoint": "", "method": ""}],
                "permissions": [{"resource": "", "action": ""}],
            }
        """
        result = {
            "new_pages": [],
            "new_components": [],
            "form_fields": [],
            "actions": [],
            "api_calls": [],
            "permissions": [],
        }

        for change in code_changes:
            if change.category != "frontend":
                continue

            patch = change.details.get("patch", "")
            file_path = change.file_path

            # 判断框架
            framework = self._detect_framework(file_path, patch)
            patterns = self.framework_patterns.get(framework, self.framework_patterns["general"])

            # 提取路由
            if change.change_type == "added":
                routes = re.findall(patterns.get("route", r'path\s*[=:]\s*["\']([^"\']+)["\']'), patch)
                for route in routes:
                    result["new_pages"].append({
                        "name": self._route_to_name(route),
                        "route": route,
                        "file": file_path,
                    })

            # 提取组件
            components = re.findall(patterns.get("component", r'function\s+(\w+)'), patch)
            for comp in components:
                if not comp.startswith("_") and comp[0].isupper():
                    result["new_components"].append({
                        "name": comp,
                        "purpose": self._infer_component_purpose(comp, patch),
                        "file": file_path,
                    })

            # 提取表单字段
            fields = re.findall(patterns.get("form_field", r'name\s*[=:]\s*["\']([^"\']+)["\']'), patch)
            for field_name in fields:
                result["form_fields"].append({
                    "field": field_name,
                    "type": self._infer_field_type(field_name, patch),
                })

            # 提取操作按钮
            actions = re.findall(patterns.get("button_action", r'onClick\s*[=:]\s*[{(]?\s*(\w+)'), patch)
            for action in actions:
                result["actions"].append({
                    "name": action,
                    "type": self._infer_action_type(action, patch),
                })

            # 提取 API 调用
            api_calls = re.findall(patterns.get("api_call", r'["\']((?:GET|POST|PUT|DELETE|PATCH)?/[^"\']+)["\']'), patch)
            for endpoint in api_calls:
                result["api_calls"].append({
                    "endpoint": endpoint,
                    "method": self._infer_http_method(endpoint, patch),
                })

            # 提取权限
            perms = re.findall(patterns.get("permission", r'permission\s*[=:]\s*["\']([^"\']+)["\']'), patch)
            for perm in perms:
                result["permissions"].append({
                    "resource": perm,
                    "action": "access",
                })

        # 去重
        for key in result:
            seen = set()
            unique = []
            for item in result[key]:
                item_str = str(item)
                if item_str not in seen:
                    seen.add(item_str)
                    unique.append(item)
            result[key] = unique

        return result

    def analyze_backend_changes(self, code_changes: list[CodeChangeInfo]) -> dict:
        """
        分析后端代码变更，提取 API 和业务规则

        Returns:
            {
                "new_apis": [{"path": "", "method": "", "description": ""}],
                "business_rules": [{"rule": "", "source": ""}],
                "data_models": [{"name": "", "fields": []}],
                "permissions": [{"resource": "", "action": ""}],
                "notifications": [{"event": "", "type": ""}],
            }
        """
        result = {
            "new_apis": [],
            "business_rules": [],
            "data_models": [],
            "permissions": [],
            "notifications": [],
        }

        for change in code_changes:
            if change.category != "backend":
                continue

            patch = change.details.get("patch", "")
            general = self.framework_patterns["general"]

            # 提取 API 路由
            if change.change_type == "added":
                api_routes = re.findall(general["api_route"], patch)
                for route in api_routes:
                    result["new_apis"].append({
                        "path": route,
                        "method": self._extract_method_from_annotation(patch, route),
                        "description": self._infer_api_description(route, patch),
                        "file": change.file_path,
                    })

            # 提取权限注解
            perms = re.findall(general["permission_annotation"], patch)
            for perm in perms:
                result["permissions"].append({
                    "resource": perm,
                    "action": "access",
                    "file": change.file_path,
                })

            # 提取校验规则
            validations = re.findall(general["validation"], patch)
            if validations:
                result["business_rules"].append({
                    "rule": f"存在 {len(validations)} 个数据校验规则",
                    "source": change.file_path,
                })

            # 提取事件/通知
            events = re.findall(general["event"], patch)
            for event in events:
                result["notifications"].append({
                    "event": event,
                    "type": self._infer_notification_type(event),
                    "file": change.file_path,
                })

        return result

    def build_operation_flow(
        self,
        feature_name: str,
        frontend_analysis: dict,
        backend_analysis: dict,
    ) -> OperationFlow:
        """
        根据代码分析结果构建操作流程

        Args:
            feature_name: 功能名称
            frontend_analysis: 前端分析结果
            backend_analysis: 后端分析结果

        Returns:
            OperationFlow
        """
        steps = []
        step_num = 1

        # 1. 入口步骤
        entry_point = "系统主菜单"
        if frontend_analysis.get("new_pages"):
            page = frontend_analysis["new_pages"][0]
            entry_point = f"导航至「{page['name']}」页面（路径：{page['route']}）"
        elif frontend_analysis.get("new_components"):
            comp = frontend_analysis["new_components"][0]
            entry_point = f"在相关页面中找到「{comp['name']}」区域"

        steps.append(OperationStep(
            step_number=step_num,
            action="进入功能页面",
            description=entry_point,
            expected_result="成功打开功能页面，看到相关操作界面",
            screenshot_hint="功能页面整体截图"
        ))
        step_num += 1

        # 2. 表单填写步骤
        if frontend_analysis.get("form_fields"):
            field_names = [f["field"] for f in frontend_analysis["form_fields"]]
            if len(field_names) <= 5:
                for field in field_names:
                    steps.append(OperationStep(
                        step_number=step_num,
                        action=f"填写「{field}」",
                        description=f"在对应输入框中输入{field}信息",
                        expected_result=f"成功填写{field}字段",
                        screenshot_hint=f"「{field}」字段截图"
                    ))
                    step_num += 1
            else:
                steps.append(OperationStep(
                    step_number=step_num,
                    action="填写表单信息",
                    description=f"依次填写以下字段：{', '.join(field_names[:5])}等",
                    expected_result="所有必填字段填写完成",
                    screenshot_hint="表单整体截图"
                ))
                step_num += 1

        # 3. 操作按钮步骤
        if frontend_analysis.get("actions"):
            for action in frontend_analysis["actions"]:
                action_desc = self._action_to_chinese(action["name"])
                steps.append(OperationStep(
                    step_number=step_num,
                    action=f"点击「{action_desc}」按钮",
                    description=f"执行{action_desc}操作",
                    expected_result=f"系统处理{action_desc}请求",
                    screenshot_hint=f"「{action_desc}」按钮截图"
                ))
                step_num += 1

        # 4. 结果确认步骤
        steps.append(OperationStep(
            step_number=step_num,
            action="确认操作结果",
            description="查看系统反馈，确认操作是否成功",
            expected_result="系统显示操作成功的提示信息",
            screenshot_hint="操作结果截图"
        ))

        # 注意事项
        notes = []
        if backend_analysis.get("permissions"):
            perm_resources = [p["resource"] for p in backend_analysis["permissions"]]
            notes.append(f"权限要求：需要 {', '.join(perm_resources)} 权限")
        if backend_analysis.get("business_rules"):
            for rule in backend_analysis["business_rules"]:
                notes.append(f"业务规则：{rule['rule']}")

        return OperationFlow(
            feature_name=feature_name,
            entry_point=entry_point,
            steps=steps,
            notes=notes,
            related_features=[]
        )

    def _detect_framework(self, file_path: str, patch: str) -> str:
        """检测前端框架"""
        if file_path.endswith(".vue"):
            return "vue"
        if any(kw in patch for kw in ["useState", "useEffect", "jsx", "React", "tsx"]):
            return "react"
        if any(kw in patch for kw in ["angular", "ngOnInit", "@Component"]):
            return "angular"
        return "general"

    def _route_to_name(self, route: str) -> str:
        """将路由路径转换为可读名称"""
        parts = route.strip("/").split("/")
        return "/".join(p.replace("-", " ").title() for p in parts if p and not p.startswith(":"))

    def _infer_component_purpose(self, name: str, patch: str) -> str:
        """推断组件用途"""
        purpose_keywords = {
            "Form": "表单", "Table": "表格", "List": "列表", "Detail": "详情",
            "Modal": "弹窗", "Dialog": "对话框", "Card": "卡片", "Chart": "图表",
            "Filter": "筛选", "Search": "搜索", "Upload": "上传", "Export": "导出",
            "Import": "导入", "Setting": "设置", "Config": "配置", "Dashboard": "仪表盘",
        }
        for keyword, purpose in purpose_keywords.items():
            if keyword.lower() in name.lower():
                return purpose
        return "通用组件"

    def _infer_field_type(self, field_name: str, patch: str) -> str:
        """推断字段类型"""
        type_keywords = {
            "email": "邮箱", "phone|mobile|tel": "电话",
            "date|time": "日期时间", "amount|price|cost|fee": "金额",
            "name|title": "文本", "desc|content|remark|note": "文本域",
            "file|attach|upload": "文件上传", "select|type|category": "下拉选择",
            "check|enable|active|status": "开关/复选",
        }
        for pattern, ftype in type_keywords.items():
            if re.search(pattern, field_name, re.IGNORECASE):
                return ftype
        return "文本输入"

    def _infer_action_type(self, action: str, patch: str) -> str:
        """推断操作类型"""
        action_keywords = {
            "submit|save|create|add": "提交/保存",
            "delete|remove": "删除", "edit|update|modify": "编辑",
            "cancel|close": "取消", "export|download": "导出",
            "import|upload": "导入", "approve|reject|review": "审批",
            "search|query|filter": "查询", "refresh|reload": "刷新",
        }
        for pattern, atype in action_keywords.items():
            if re.search(pattern, action, re.IGNORECASE):
                return atype
        return "通用操作"

    def _infer_http_method(self, endpoint: str, patch: str) -> str:
        """推断 HTTP 方法"""
        if re.search(r'(?:POST|post)', patch[:500]):
            return "POST"
        if re.search(r'(?:PUT|put|PATCH|patch)', patch[:500]):
            return "PUT"
        if re.search(r'(?:DELETE|delete)', patch[:500]):
            return "DELETE"
        return "GET"

    def _extract_method_from_annotation(self, patch: str, route: str) -> str:
        """从注解中提取 HTTP 方法"""
        match = re.search(r'@(Get|Post|Put|Delete|Patch|RequestMapping)\s*\([^)]*\b' + re.escape(route), patch)
        if match:
            method = match.group(1).upper()
            if method == "REQUESTMAPPING":
                method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', patch)
                return method_match.group(1) if method_match else "GET"
            return method
        return "GET"

    def _infer_api_description(self, route: str, patch: str) -> str:
        """推断 API 描述"""
        # 尝试从注释中提取
        comment_match = re.search(r'(?:/\*\*|//)\s*(.+?)\n', patch)
        if comment_match:
            return comment_match.group(1).strip()
        return f"{route} 接口"

    def _infer_notification_type(self, event: str) -> str:
        """推断通知类型"""
        if any(kw in event.lower() for kw in ["email", "mail"]):
            return "邮件通知"
        if any(kw in event.lower() for kw in ["sms", "message"]):
            return "短信通知"
        if any(kw in event.lower() for kw in ["webhook", "callback"]):
            return "Webhook 回调"
        return "系统通知"

    def _action_to_chinese(self, action: str) -> str:
        """将操作名翻译为中文"""
        action_map = {
            "submit": "提交", "save": "保存", "create": "创建", "add": "添加",
            "delete": "删除", "remove": "移除", "edit": "编辑", "update": "更新",
            "cancel": "取消", "close": "关闭", "export": "导出", "import": "导入",
            "upload": "上传", "download": "下载", "approve": "审批通过",
            "reject": "驳回", "search": "搜索", "query": "查询", "filter": "筛选",
            "refresh": "刷新", "confirm": "确认", "publish": "发布",
            "archive": "归档", "restore": "恢复", "share": "分享",
        }
        action_lower = action.lower()
        for eng, chn in action_map.items():
            if eng in action_lower:
                return chn
        return action
