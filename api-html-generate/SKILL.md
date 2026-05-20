---
name: api-html-generate
description: api html, api doc html, html api document, api change html, html接口文档, 接口说明页, 接口变更说明页, API 文档 HTML, 生成 API HTML. Use ONLY when the task is to create or update a standalone HTML page for API documentation or API change notes.
metadata:
  when_to_use: "Use when the user asks for api html, api doc html, html api document, api change html, html接口文档, 接口说明页, 接口变更说明页, API 文档 HTML, 生成 API HTML, 生成接口 HTML, 输出接口说明页."
---

# API HTML Generate

## Overview

本 Skill 只用于生成或更新 API 说明 HTML 页面。

它的职责是：

- 根据接口信息生成一份结构清晰、可直接阅读的独立 HTML 文档
- 区分“新增 API 说明”和“修改 API 说明”两种场景
- 对新增 API 输出相对完整的接口说明
- 对修改 API 只聚焦本次实际改动部分，不重复展开未变化内容
- 保持输出结构稳定、视觉风格统一、信息层级清晰

本 Skill 不绑定具体项目、具体返回包裹结构、具体字段命名规范或具体文件命名规则。

## Trigger Conditions

以下场景优先触发本 Skill：

- 用户要求生成 `api html`
- 用户要求生成 `api doc html`
- 用户要求生成 `html api document`
- 用户要求生成 `api change html`
- 用户要求生成 `html接口文档`
- 用户要求生成 `接口说明页`
- 用户要求生成 `接口变更说明页`
- 用户要求生成 `API 文档 HTML`
- 用户要求生成 `API HTML`
- 用户要求生成 `接口 HTML`

以下场景通常不适用本 Skill：

- 只需要 Markdown 文档
- 只需要 OpenAPI / Swagger / YAML / JSON 描述
- 只需要简单接口摘要而不需要独立 HTML 页面

## Workflow Decision

先判断当前任务属于哪一种：

### 1. 新增 API 说明

适用场景：

- 用户描述一个新接口
- 用户要求补齐完整接口说明
- 用户要求把散乱接口信息整理成完整 HTML 页面

输出要求：

- 应生成一份相对完整的 API 说明 HTML
- 需覆盖接口用途、路径、方法、认证、参数、响应、异常、示例等核心信息

### 2. 修改 API 说明

适用场景：

- 用户描述已有接口的变更
- 用户要求输出接口更新说明、字段变更说明、兼容性说明

输出要求：

- 只说明本次修改部分
- 不要把整份 API 文档重新展开，除非用户明确要求
- 每一项变更必须说清楚改了什么、影响什么、调用方需要注意什么

## Global Rules

- 输出格式始终为单文件 HTML。
- 默认使用用户当前对话语言；若用户未指定，中文优先。
- 视觉风格必须参考 `.agents/skills/api-html-generate/references/design.md`。
- 结构模板必须参考 `.agents/skills/api-html-generate/references/templates.md`。
- 不要自由发挥成任意网页，必须优先保证“接口信息可读、可查、可复制、可对照”。
- 不要编造用户未提供的接口事实；信息不足时使用“待补充”“未确认”“未提供”明确标注。
- 对修改 API，只说明本次有变化的部分；不要为了显得完整而重复未变化内容。
- 对新增 API，信息说明应相对完整，但仍不得臆造事实。
- 输出必须是可直接保存并打开的完整 HTML，包含基础样式。

## Design Requirements

生成 HTML 时必须遵守以下原则：

- 页面应包含清晰的头部摘要区。
- 顶部应明确展示接口名称、请求方式、路径和关键标签。
- 文档主体应按主题分节，而不是把所有内容堆成一张大表。
- 表格用于字段说明、状态说明、变更项说明。
- 说明性信息使用 note / warning 区块强调。
- 请求和响应示例使用独立代码块展示。
- 页面需兼顾桌面与移动端阅读。

具体视觉语言、版式和组件约束见：

- `.agents/skills/api-html-generate/references/design.md`

## Output Structure

必须根据任务类型选择对应模板：

- 新增 API：使用“新增 API HTML 模板”
- 修改 API：使用“修改 API HTML 模板”

详细模板见：

- `.agents/skills/api-html-generate/references/templates.md`

## New API HTML Requirements

新增 API HTML 通常应包含：

- 接口名称
- 接口用途摘要
- 请求方式
- 接口路径
- 鉴权要求
- 请求参数说明
- 响应结构说明
- 关键字段说明
- 异常 / 错误说明
- 请求示例
- 响应示例

如果字段层级复杂，可拆成：

- 顶层字段
- 列表项字段
- 嵌套对象字段
- 补充说明

## Modified API HTML Requirements

修改 API HTML 只聚焦本次改动。

必须优先说明以下内容中实际发生变化的部分：

- 接口路径变更
- 请求方式变更
- 认证要求变更
- 请求参数新增 / 删除 / 调整
- 响应字段新增 / 删除 / 调整
- 错误码或异常说明变更
- 示例变化
- 兼容性影响

处理原则：

- 只写实际变更项
- 每项变更都写清楚“变更前 / 变更后 / 影响说明”
- 未变化部分不要重复铺开
- 若信息缺失，明确标注“未提供”或“待补充”

## Quality Checklist

输出前逐项自检：

- 是否已正确判断为“新增 API”或“修改 API”
- 是否输出了完整 HTML，而不是 Markdown 或半截片段
- 是否参考了 `design.md` 的视觉风格
- 是否使用了对应场景的模板
- 是否没有编造接口事实
- 修改 API 是否只说明了修改部分
- 新增 API 是否已经相对完整地说明了接口核心信息
- 表格、说明块、代码块是否清晰可读
- 页面在移动端阅读时是否仍能正常浏览

## Response Style

- 以“可以直接给研发、测试、前端、对接方阅读”为目标。
- 信息顺序清晰，先总览后细节。
- 视觉上要整洁、专业、克制，不做花哨展示。
- 不输出与接口说明无关的装饰内容。

## Resources

- `.agents/skills/api-html-generate/references/design.md`
- `.agents/skills/api-html-generate/references/templates.md`
