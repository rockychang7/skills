---
name: requirement-markdown-architect
description: 将大需求或模糊需求梳理成按功能模块展开的完整 Markdown 文档。适用于需求分析、需求评审、PRD 整理、模块拆解，以及补充每个模块“要做什么、有什么问题、有什么注意点”。
---

# Requirement Markdown Architect

## Context

先整理：

- 背景、目标、角色、范围、依赖、约束、已知问题
- `已确认`、`推断`、`待确认`

缺少关键信息时只提少量关键问题；其余内容保留 `待确认`，不要编造业务细节。

## Split Modules

- 优先使用用户已有模块
- 没有模块时，按业务能力、角色、流程或数据归属拆分
- 先给模块总览：`模块`、`目标`、`优先级`、`依赖`、`风险`

不要把多个独立业务混成一个模块，也不要把单个按钮、字段单独拆成模块。

## Analyze Modules

每个模块至少写清：

- 模块目标
- 适用角色、前置条件、触发条件
- 功能点清单
- 每个功能点具体要做什么
- 关键规则、边界、异常路径
- 已知问题、待确认项
- 实现、联调、测试注意点
- 对其他模块的影响

复杂流程使用 `mermaid flowchart TD`。

## Output Rules

- 输出 Markdown
- 优先按 [references/output-template.md](references/output-template.md) 组织
- 模块说明保持同一结构，避免只写总览不写细节
- 如果用户已明确术语或边界，保持原词
- 如果要落库文档，优先作为 `spec.md` 主体

## Quality Checklist

- 是否区分 `已确认`、`推断`、`待确认`
- 是否按模块逐项展开
- 是否写清“做什么、问题、注意点”
- 是否写出依赖、边界、异常场景
- 是否避免臆造接口、字段、规则

## Resources

- 使用 [references/output-template.md](references/output-template.md) 作为最终 Markdown 骨架
- 使用 [references/discovery-checklist.md](references/discovery-checklist.md) 补齐信息收集与待确认项
