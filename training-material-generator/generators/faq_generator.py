"""
FAQ 文档生成器
生成 FAQ 文档（Markdown 格式）
"""

import logging
from collections import defaultdict
from pathlib import Path

from models import TrainingMaterial, FAQItem

logger = logging.getLogger(__name__)


class FAQGenerator:
    """FAQ 文档生成器"""

    # FAQ 分类图标
    CATEGORY_ICONS = {
        "操作类": "🔧",
        "限制类": "⛔",
        "场景类": "💡",
        "异常类": "🚨",
    }

    def generate(self, material: TrainingMaterial, output_path: str) -> str:
        """
        生成 FAQ 文档

        Args:
            material: 培训材料数据
            output_path: 输出文件路径

        Returns:
            生成的文件路径
        """
        lines = []

        # ====== 文档头部 ======
        lines.append(f"# ❓ 常见问题 (FAQ)")
        lines.append(f"\n**版本：** {material.version}")
        lines.append(f"**日期：** {material.release_date}")
        lines.append(f"\n---\n")
        lines.append(f"## 📋 本次更新概览")
        lines.append(f"\n{material.summary}\n")

        # ====== 按分类分组 ======
        faq_by_category = defaultdict(list)
        for faq in material.faqs:
            faq_by_category[faq.category].append(faq)

        # ====== 按分类输出 ======
        for category, faqs in faq_by_category.items():
            icon = self.CATEGORY_ICONS.get(category, "📌")
            lines.append(f"\n---\n")
            lines.append(f"## {icon} {category}\n")

            for i, faq in enumerate(faqs, 1):
                lines.append(f"### Q{i}: {faq.question}\n")
                lines.append(f"**A:** {faq.answer}\n")

        # ====== 联系方式 ======
        lines.append("\n---\n")
        lines.append("## 📞 获取帮助")
        lines.append("")
        lines.append("如果以上 FAQ 没有解决您的问题，请通过以下渠道获取帮助：")
        lines.append("")
        lines.append("- 📧 邮件：联系您的客户成功经理")
        lines.append("- 💬 即时通讯：通过系统内置的在线客服")
        lines.append("- 📝 工单：提交支持工单")
        lines.append("")

        # 保存
        content = "\n".join(lines)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"FAQ 文档已生成: {output_path}")
        return output_path
