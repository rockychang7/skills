# Code Review 输出模板

## 无明确问题时

```md
## Findings

- 未发现明确问题。

## Rule Compliance Checklist

- 架构与模块边界：符合 / 不适用
- 技术栈与版本兼容：符合 / 不适用
- DAO / Repository / Mapper / XML / SQL：符合 / 不适用
- 日志与异常：符合 / 不适用
- SQL Schema / DDL 生成产物：符合 / 不适用
- API 文档 / 接口快照生成产物：符合 / 不适用
- 文档与实现一致性：符合 / 不适用

## Approval Needed

- 无。

## Residual Risks

- 若存在环境、上下文或验证范围限制，必须在此补充；否则写“无”。

## Testing Gaps

- 若存在从静态评审角度识别出的验证缺口，必须列出；否则写“无”。
```

## 存在问题时

```md
## Findings

### [P1] 标题
- 文件：
- 行号：
- 规则维度：
- 问题：
- 影响：
- 处置建议：auto_fix / require_approval / report_only
- 建议：

### [P2] 标题
- 文件：
- 行号：
- 规则维度：
- 问题：
- 影响：
- 处置建议：auto_fix / require_approval / report_only
- 建议：

## Rule Compliance Checklist

- 架构与模块边界：符合 / 不符合 / 不适用
- 技术栈与版本兼容：符合 / 不符合 / 不适用
- DAO / Repository / Mapper / XML / SQL：符合 / 不符合 / 不适用
- 日志与异常：符合 / 不符合 / 不适用
- SQL Schema / DDL 生成产物：符合 / 不符合 / 不适用
- API 文档 / 接口快照生成产物：符合 / 不符合 / 不适用
- 文档与实现一致性：符合 / 不符合 / 不适用

## Approval Needed

- finding：
- 影响范围：
- 建议动作：
- 原因：为什么不能继续自动修复
- 后续验证重点：

## Residual Risks

- 风险：

## Testing Gaps

- 缺失测试：
```

## 输出要求

- `Findings` 必须放在最前面，严禁先写总结。
- 每个明确问题都必须给出严重级别与处置建议。
- 若某个规则维度结果为 `不符合`，必须在 `Findings` 中有对应具体问题。
- 若存在 `require_approval` 的 finding，必须在 `Approval Needed` 中逐项汇总。
- `Residual Risks` 用于说明当前仍然存在但未被当前 review 关闭的风险。
- `Testing Gaps` 只说明静态评审识别出的验证缺口，不等于已经完成测试验收。
- 如果当前模式为 `review-only`，输出模板内容后必须停止，不得追加自动修复动作说明。
