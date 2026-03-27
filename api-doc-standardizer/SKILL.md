---
name: api-doc-standardizer
description: standardize markdown api documentation from natural-language interface descriptions for any general api, internal service api, backend api, client-facing api, or third-party integration api. use when needs to generate complete documentation for a newly added api, write detailed change notes for a modified api, enforce snake_case field naming, or apply a fixed response envelope with timestamp, ret_code, ret_msg, and data.
---

# API Doc Standardizer

## Overview

将自然语言接口描述整理成统一、可复用的 Markdown API 文档。
优先区分“新增 API”与“修改 API”两种场景，并严格按对应模板输出。
此技能适用于通用 API 文档场景，不绑定任何特定厂商、平台或框架。

## Workflow Decision

1. 先判断任务类型：
   - **新增 API**：用户在描述一个新接口，或要求补齐完整接口文档。
   - **修改 API**：用户在描述已有接口的变更，或要求输出更新说明、变更说明、改动记录。
2. 若用户没有明确说明类型，则根据描述推断：
   - 出现“新增、创建、提供一个接口、补一份接口文档”等表述时，按**新增 API**处理。
   - 出现“修改、调整、变更、字段新增、字段删除、返回结构变化、错误码更新”等表述时，按**修改 API**处理。
3. 信息不足时，不要凭空补造业务事实。可以保留“待补充”占位，但仍须按固定模板输出。

## Global Rules

- 输出格式始终使用 **Markdown**。
- 默认使用用户当前对话语言；若用户未指定，中文优先。
- 所有参数字段、响应字段、示例 JSON 字段统一转换为 **snake_case**。
- 如果用户原始描述使用 camelCase、PascalCase 或混合命名，输出时统一转为 snake_case，并保持字段语义不变。
- 接口名称、路径、业务含义不要擅自改写；仅字段命名风格做统一化处理。
- 对模糊信息使用“待补充”“未提供”“需确认”明确标注。
- 不要混用“新增文档模板”和“修改说明模板”。
- 修改场景的重点是**把所有涉及到的变更逐项说清楚**，不要只写一句“接口已更新”。
- 除非用户明确提供了不同响应包裹结构，否则默认使用标准响应结构：`timestamp`、`ret_code`、`ret_msg`、`data`。
- 如果用户描述中的响应顶层字段与标准响应结构冲突，优先保留用户明确要求，并在文档中注明“此接口未使用默认标准响应结构”。

## Standard Response Envelope

默认标准响应结构如下：

```json
{
  "timestamp": 1764746887924,
  "ret_code": 200000,
  "ret_msg": "",
  "data": null
}
```

生成文档时遵守这些规则：

- `timestamp`：响应时间戳，通常为毫秒级时间戳。
- `ret_code`：业务返回码。若用户未提供，成功示例默认可使用 `200000`。
- `ret_msg`：返回信息。若用户未提供，成功示例可为空字符串或成功说明。
- `data`：业务数据主体。若无业务数据，可为 `null`。
- 新增 API 文档中的“响应”部分，应先描述标准响应结构，再展开 `data` 字段的内部结构。
- 修改 API 文档中，如响应结构有变化，必须明确说明标准响应层是否变化，以及 `data` 内字段是否变化。

详细模板与示例见 `references/templates.md`。

## New API Documentation

当任务是新增 API 时，必须输出完整文档，并严格覆盖以下部分：

1. 接口名称
2. URL
3. 请求方式
4. 参数
5. 响应
6. 示例
7. 异常说明

参数与响应部分应尽量结构化展示，推荐表格；若字段层级复杂，可使用分层列表补充说明。

生成时遵守这些规则：

- URL 写明确路径；若未提供域名，只保留接口路径。
- 请求方式只写标准方法，如 `GET`、`POST`、`PUT`、`DELETE`。
- 参数至少说明：参数名、类型、是否必填、说明。
- 参数名一律输出为 snake_case。
- 响应至少说明：字段名、类型、说明。
- 响应部分默认先列出 `timestamp`、`ret_code`、`ret_msg`、`data` 四个顶层字段。
- `data` 内部字段按用户提供信息继续展开，并统一为 snake_case。
- 示例至少包含一个请求示例或响应示例；理想情况下两者都给。
- 请求示例与响应示例中的 JSON 字段全部使用 snake_case。
- 异常说明至少列出异常场景和对应含义；若用户未提供错误码，可写“未提供具体错误码”。

详细模板与示例见 `references/templates.md`。

## API Modification Documentation

当任务是修改 API 时，不要重复输出整份新增接口文档，除非用户明确要求。
默认输出“变更说明”文档，但是特别注意必须标注接口的url,并覆盖所有受影响项。

必须检查并说明是否涉及以下内容：

- 接口路径有变更时特别说明
- 请求方式变更
- 请求参数新增
- 请求参数删除
- 请求参数类型、含义、是否必填发生变化
- 请求字段命名风格是否需要统一为 snake_case
- 响应顶层标准结构是否变化
- 响应字段新增
- 响应字段删除
- 响应字段类型、层级、含义发生变化
- 示例更新
- 异常说明或错误码变更
- 兼容性影响

输出时遵守这些规则：

- 只写实际发生的变更项，不要为了凑格式虚构不存在的改动。
- 每一项变更都写清楚“变更前 / 变更后 / 影响说明”中的至少两项；如果变更前信息缺失，明确标注“变更前未提供”。
- 若某次修改同时影响参数、响应、异常说明，必须分别列出，不能合并成一句笼统描述。
- 若字段命名从驼峰改为下划线，必须作为明确变更项写出。
- 若变更可能影响现有调用方，必须写出兼容性影响或升级提示。

详细模板与示例见 `references/templates.md`。

## Quality Checklist

输出前逐项自检：

- 是否已经正确判断为“新增 API”或“修改 API”
- 是否使用 Markdown 输出
- 所有字段是否都已统一为 snake_case
- 新增 API 是否包含 URL、请求方式、参数、响应、示例、异常说明
- 响应是否按标准结构 `timestamp`、`ret_code`、`ret_msg`、`data` 组织
- 修改 API 是否覆盖全部已提及的变更点
- 是否对未知信息使用了明确占位，而不是臆造内容
- 是否避免把修改说明写成完整接口文档

## Response Style

- 以可直接落库、可直接发给研发、测试、前端、第三方对接方为目标。
- 标题清晰，层级稳定，避免冗长废话。
- 表格字段尽量统一，方便后续复制到 wiki、git 仓库或接口平台。
- 不要把该技能描述为特定厂商专用规范；默认按通用 API 文档规范执行。

## Resources

- `references/templates.md`：新增 API 文档模板、修改说明模板、以及示例输出。
