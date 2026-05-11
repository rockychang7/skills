---
name: cunxin-code-review-skill
description: 在当前仓库中，当后端代码任务进入完整 Code Review 阶段，或用户明确要求 review / code review / pr review / 变更评审时，使用此 skill 完成完整静态评审：识别变更类型，按需加载 ARCHITECTURE、BACKEND 与命中的 backend-rules，检查规则违规、代码设计质量、隐藏 Bug 和回归风险，输出 Findings、Rule Compliance Checklist、Approval Needed、Residual Risks、Testing Gaps，并为每个问题给出处置建议。
---

# Cunxin Code Review Skill

## Overview

本 Skill 只适用于当前项目后端代码的完整 Code Review，不适用于轻量 review / 自审。

本 Skill 是当前项目完整 Code Review 的主执行体；`../../../docs/backend-rules/07-code-review-best-practice.md` 只负责说明完整 Code Review 的定位、边界、关注点和输出原则。

若当前运行环境支持 `sub agent`，应优先由独立 `sub agent` 承载本 Skill 的执行；若不支持，则由当前 Agent 直接执行，但评审范围、输出结构和处置边界保持不变。

本 Skill 的目标不是复述代码做了什么，而是识别：

- 规则违规
- 代码设计质量问题
- 隐藏 Bug
- 兼容性风险
- 数据一致性风险
- 回归风险
- 测试缺口

本 Skill 只负责评审与处置建议，不直接自动修改代码、提交代码或替代测试验收。

## Trigger Conditions

以下场景默认触发本 Skill：

- 用户明确要求 `review`、`code review`、`pr review`、`变更评审`
- 当前后端代码任务进入质量闭环中的完整 Code Review 阶段
- 中高风险后端代码变更
- 低风险但用户明确要求 review 的后端代码任务

以下场景默认不触发本 Skill，而是走轻量 review / 自审：

- 低风险、影响边界清晰且未被用户明确要求 review 的小改动
- 纯文档、纯注释、纯格式调整、纯分析类任务

## Severity Guide

- `P0`：确定会导致生产故障、数据错乱、严重安全问题，必须阻塞交付
- `P1`：高概率导致功能错误、兼容性问题、重要流程异常，原则上阻塞交付
- `P2`：存在明显风险、规则违规或维护成本问题，通常应在当前迭代处理
- `P3`：优化项、可读性或一致性问题，默认不阻塞交付

## Workflow

### 1. 建立上下文

- 读取本次需求、缺陷描述、任务范围和已确认结论
- 读取当前代码 diff、关联文件和必要上下文
- 读取 `../../../docs/ARCHITECTURE.md`
- 读取 `../../../docs/BACKEND.md`
- 若存在 `spec.md`、`plan.md`、`task.md`、`tasks.md` 或 `task-xx-<topic>.md`，必须对照其已确认内容检查实现是否一致
- 明确当前调用属于以下哪种模式：
  - `review-only`
  - `质量闭环中的完整 Code Review`

### 2. 识别变更类型并加载专项规则

- 必须始终加载：
  - `../../../docs/ARCHITECTURE.md`
  - `../../../docs/BACKEND.md`
  - `../../../docs/backend-rules/07-code-review-best-practice.md`
- 按变更类型继续加载：
  - 代码设计与职责拆分：`../../../docs/backend-rules/02-code-design-best-practice.md`
  - 技术栈与版本兼容：`../../../docs/backend-rules/01-tech-stack.md`
  - DAO / Repository / Mapper / XML / SQL：`../../../docs/backend-rules/03-dao-best-practice.md`
  - 日志与异常：`../../../docs/backend-rules/04-log-exception-best-practice.md`
  - SQL schema / DDL 生成产物：`../../../docs/backend-rules/05-sql-schema-generation-rule.md`
  - API 文档 / 接口快照生成产物：`../../../docs/backend-rules/06-api-doc-generation-rule.md`

### 3. 执行两条主线评审

- 主线一：规则符合性评审
  - 架构与模块边界
  - 代码设计质量：高内聚低耦合、职责边界、方法粒度、抽象复用、耦合控制
  - 技术栈与版本兼容
  - DAO / Repository / Mapper / XML / SQL
  - 日志与异常
  - SQL schema / DDL 生成产物
  - API 文档 / 接口快照生成产物
  - 文档与实现一致性
- 主线二：风险与回归评审
  - 业务正确性与异常路径
  - 跨模块与调用链影响
  - 数据一致性与兼容性
  - 性能、副作用与可观测性

### 4. 对 findings 分级与处置

- 每个明确问题必须给出严重级别：`P0`、`P1`、`P2`、`P3`
- 每个明确问题必须给出处置建议：
  - `auto_fix`
  - `require_approval`
  - `report_only`
- 处置建议必须遵守 `../../../docs/WORKFLOW.md` 中的 disposition / approval 规则，并遵守 `../../../docs/backend-rules/07-code-review-best-practice.md` 中的输出原则
- 本 Skill 只能给出处置建议，不能绕过工作流自行决定扩大范围或继续自动修改

### 5. 输出固定结果

必须按以下顺序输出：

1. `Findings`
2. `Rule Compliance Checklist`
3. `Approval Needed`
4. `Residual Risks`
5. `Testing Gaps`

输出时遵守以下要求：

- 必须先读取并遵守 `references/review-output-template.md` 中定义的固定输出模板。
- findings 必须优先于总结
- 每个 finding 必须给出：文件、位置、规则维度、问题、影响、处置建议、建议动作
- 若某个规则维度检查结果为 `不符合`，必须在 findings 中给出具体问题
- 若存在 `require_approval` 的 finding，必须在 `Approval Needed` 中单独汇总范围、影响和建议动作
- 若没有发现明确问题，必须明确写出“未发现明确问题”
- 若当前模式为 `review-only`，输出结果后必须停止，不得继续自动修改代码

## Hard Rules

- 不要把完整 Code Review 降级成普通摘要
- 不要跳过任一规则维度而不说明原因
- 不要忽略 `Controller` / `Service` / `Manager` 中的大方法、职责混杂、错误抽象或高耦合信号
- 不要忽略 XML、Mapper、配置、常量、异常码、任务文档和生成产物
- 不要把测试验收动作混进 Code Review 中
- 不要在 `review-only` 场景下擅自修改代码
- 不要把需要用户审批的问题伪装成可自动修复问题

## Resources

- `../../../docs/backend-rules/07-code-review-best-practice.md`
- `../../../docs/backend-rules/02-code-design-best-practice.md`
- `../../../docs/WORKFLOW.md`
- `../../../docs/BACKEND.md`
- `../../../docs/ARCHITECTURE.md`
- `references/review-output-template.md`
