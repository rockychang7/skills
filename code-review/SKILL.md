---
name: code-review
description: review, code review, review code, review changes, diff review, patch review, pr review, 代码评审, 代码审查, 变更评审, PR评审. Use when evaluating code changes against repository requirements and engineering rules, and when a structured review report with findings and compliance status is needed.
metadata:
  when_to_use: "Use when the user asks for review, code review, review code, review changes, diff review, patch review, PR review, 代码评审, 代码审查, 变更评审, PR评审, 审查改动, 检查改动."
---

# Code Review Skill

## Overview

本 Skill 用于执行完整的代码评审。

它的职责是：

- 识别当前改动中的明确问题和风险
- 检查改动是否符合仓库内的硬性要求和命中的专项规则
- 输出结构化 Code Review 报告
- 明确核心规则是否符合，以及哪些地方不符合

本 Skill 不绑定具体项目、具体技术栈或具体目录结构。

使用时，必须先结合当前仓库自己的项目规则、架构文档、代码规范、任务文档和变更上下文综合判断，不能把本 Skill 当作脱离上下文的通用摘要器。

## Trigger Conditions

以下场景优先触发本 Skill：

- 用户明确要求 `review`
- 用户明确要求 `code review`
- 用户明确要求 `review code`
- 用户明确要求 `review changes`
- 用户明确要求 `diff review`
- 用户明确要求 `patch review`
- 用户明确要求 `pr review`
- 用户明确要求 `代码评审`
- 用户明确要求 `代码审查`
- 用户明确要求 `变更评审`
- 用户明确要求 `PR评审`
- 当前任务进入完整 Code Review 阶段
- 当前改动范围较大、风险较高，或需要正式评审结论

以下场景通常不需要触发本 Skill：

- 低风险、小范围且用户未要求正式 review 的改动
- 纯文档、纯注释、纯格式整理
- 只需要快速自检、且不需要形成正式 review 报告的场景

## Review Goals

本 Skill 的目标不是复述代码做了什么，而是判断：

- 是否违反项目或任务的硬性要求
- 是否存在明确 Bug、回归风险或隐含风险
- 是否存在设计、边界、可维护性问题
- 是否存在数据一致性、安全、性能或兼容性问题
- 是否存在测试缺口

## Workflow

### 1. 建立评审上下文

- 先读取当前任务描述、用户要求、已确认约束和任务文档。
- 优先识别本次 review 属于：
  - `review-only`
  - 质量闭环中的正式 Code Review
- 如果仓库中存在架构文档、项目规则、语言规则、测试规则、API 规则、数据库规则等，必须按改动命中范围继续读取。

### 2. 识别改动范围

优先通过以下方式识别当前任务的实际改动：

- `git status`
- `git diff --stat`
- `git diff --name-only`
- `git diff`
- `git diff --cached`
- 必要时使用 `git log --oneline -10`

如果当前环境不适合使用 Git diff，则至少基于用户提供的补丁、变更文件列表或任务文档建立评审范围。

### 3. 加载命中的规则

- 优先加载仓库自己的硬性要求和项目特有规则。
- 再按当前改动命中语言、框架、数据库、API、安全、测试等专项规则。
- 不要机械全量读取所有规则，只读取与当前改动直接相关的部分。

### 4. 执行评审

必须沿两条主线执行：

- 主线一：规则与要求符合性评审
- 主线二：缺陷、回归与风险评审

### 5. 产出报告

Code Review 完成后，必须输出一份结构化报告。

报告必须包含：

1. `Findings`
2. `Core Rule Compliance`
3. `Approval Needed`
4. `Residual Risks`
5. `Testing Gaps`

## Review Focus

至少覆盖以下维度：

- 项目 / 任务硬性要求
- 架构与模块边界
- 正确性与缺陷风险
- 代码质量与可维护性
- 数据与状态一致性
- 安全与权限控制
- 性能与资源使用
- 测试与验证要求
- 文档 / 配置 / 兼容性

如果某个维度与当前改动无关，可以标记为 `不适用`，但不能无说明跳过。

## Severity Guide

- `P0`：确定会导致严重故障、数据损坏、严重安全问题，必须阻塞交付
- `P1`：高概率导致功能错误、兼容性问题、关键流程异常，原则上阻塞交付
- `P2`：存在明显风险、规则违规或维护成本问题，通常应在当前迭代处理
- `P3`：优化项、一致性问题、轻度可维护性问题，默认不阻塞交付

## Disposition Guidance

每个明确问题都必须给出处置建议：

- `auto_fix`
- `require_approval`
- `report_only`

判定原则：

- `auto_fix`：问题明确、修复路径单一、不会引入额外业务决策，也不会意外扩大 API / 数据 / 安全 / 架构影响范围
- `require_approval`：修复涉及业务语义、接口契约、数据结构、安全策略、范围扩大，或与其他规则 / 事实存在冲突
- `report_only`：问题成立，但属于历史技术债、当前任务明确不处理范围，或当前信息不足以安全落地修改

## Output Requirements

- 必须先读取并遵守 `.agents/skills/code-review/references/review-output-template.md` 中定义的模板。
- 输出必须是一份明确的 Code Review 报告，不能只给摘要。
- `Findings` 必须优先于总结输出。
- 每个明确问题必须给出：文件、位置、规则维度、问题、影响、处置建议、建议动作。
- `Core Rule Compliance` 必须逐项说明核心规则是否符合。
- 若某项核心规则结果为 `不符合`，必须在 `Findings` 中给出对应具体问题。
- 若存在 `require_approval` 的 finding，必须在 `Approval Needed` 中单独汇总。
- 若没有发现明确问题，必须明确写出“未发现明确问题”。
- 若当前模式为 `review-only`，输出报告后必须停止，不得自动继续修改代码。

## Hard Rules

- 不要把 Code Review 降级成变更摘要
- 不要跳过命中的仓库硬性要求
- 不要忽略改动相关的配置、脚本、测试、文档和生成产物
- 不要把测试验收动作混进 Code Review 结论里
- 不要在 `review-only` 场景下擅自修改代码
- 不要把需要审批的问题伪装成可自动修复问题

## Resources

- `.agents/skills/code-review/references/review-output-template.md`
