"""
视频脚本生成器
生成演示视频的旁白脚本（Markdown 格式）
"""

import logging
from pathlib import Path

from models import TrainingMaterial, FeatureInfo, BusinessValue, OperationFlow

logger = logging.getLogger(__name__)


class VideoScriptGenerator:
    """演示视频脚本生成器"""

    def generate(self, material: TrainingMaterial, output_path: str) -> str:
        """
        生成演示视频脚本

        Args:
            material: 培训材料数据
            output_path: 输出文件路径

        Returns:
            生成的文件路径
        """
        lines = []

        # ====== 文档头部 ======
        lines.append(f"# 🎬 系统更新培训 — 演示视频脚本")
        lines.append(f"\n**版本：** {material.version}")
        lines.append(f"**日期：** {material.release_date}")
        lines.append(f"\n---\n")
        lines.append(f"## 📋 整体概览")
        lines.append(f"\n{material.summary}\n")

        # ====== 逐功能脚本 ======
        for i, feature in enumerate(material.features, 1):
            bv = material.business_values.get(feature.name)
            flow = material.operation_flows.get(feature.name)

            lines.append(f"\n---\n")
            lines.append(f"## 功能 {i}：{feature.name}")
            lines.append(f"\n> 优先级：{feature.priority.value}\n")

            # --- 开场 ---
            lines.append("### 🎬 开场白（15-30秒）\n")
            if bv:
                lines.append(f"> {bv.value_proposition}")
            else:
                lines.append(f"> 本次更新带来了「{feature.name}」功能，让我们来看看它能如何帮助您提升工作效率。")
            lines.append("")

            # --- 场景引入 ---
            lines.append("### 🎬 场景引入（30-60秒）\n")
            if bv:
                lines.append(f"**痛点描述：**\n")
                lines.append(f"> 想象一下，当你需要处理{feature.description}的时候——\n")
                lines.append(f"> {bv.before_scenario}\n")
                lines.append(f"\n**现在：**\n")
                lines.append(f"> {bv.after_scenario}\n")
            lines.append("")

            # --- 功能演示 ---
            lines.append("### 🎬 功能演示（2-5分钟）\n")
            if flow:
                lines.append(f"**功能入口：** {flow.entry_point}\n")
                lines.append("**操作步骤：**\n")
                for step in flow.steps:
                    lines.append(f"**步骤 {step.step_number}：{step.action}**\n")
                    lines.append(f"- 操作说明：{step.description}")
                    lines.append(f"- 预期结果：{step.expected_result}")
                    if step.screenshot_hint:
                        lines.append(f"- 📸 截图建议：{step.screenshot_hint}")
                    lines.append("")

                    # 旁白
                    narration = self._generate_step_narration(step, feature)
                    lines.append(f"> 🎙️ 旁白：{narration}\n")
            lines.append("")

            # --- 价值总结 ---
            lines.append("### 🎬 价值总结（15-30秒）\n")
            if bv:
                lines.append(f"> 通过「{feature.name}」功能，{bv.value_proposition}")
                if bv.key_benefits:
                    lines.append("\n**关键收益：**")
                    for benefit in bv.key_benefits:
                        lines.append(f"- ✅ {benefit}")
            lines.append("")

            # --- 注意事项 ---
            if flow and flow.notes:
                lines.append("### ⚠️ 注意事项\n")
                for note in flow.notes:
                    lines.append(f"- {note}")
                lines.append("")

        # ====== 结尾 ======
        lines.append("\n---\n")
        lines.append("## 🎬 结尾（10秒）\n")
        lines.append("> 以上就是本次更新的全部功能介绍。")
        lines.append("> 如有任何问题，请通过内部支持渠道反馈，我们将尽快为您解答。")
        lines.append("> 感谢您的使用！\n")

        # 保存
        content = "\n".join(lines)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"视频脚本已生成: {output_path}")
        return output_path

    def _generate_step_narration(self, step, feature: FeatureInfo) -> str:
        """为操作步骤生成旁白"""
        templates = [
            f"接下来，我们{step.action}。{step.description}。",
            f"现在请{step.action}。完成后，您应该能看到{step.expected_result}。",
            f"然后，{step.action}——{step.description}。",
        ]
        # 根据步骤号选择不同模板
        return templates[step.step_number % len(templates)]
