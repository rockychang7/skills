# API Documentation Templates

## 标准响应结构

默认标准响应结构如下：

```json
{
  "timestamp": 1764746887924,
  "ret_code": 200000,
  "ret_msg": "",
  "data": null
}
```

除非用户明确要求其他顶层结构，否则新增 API 文档和示例响应都按此结构组织。

## 新增 API 文档模板

严格按以下结构输出：

- 不得调整顶层章节顺序。
- 不得删除任一固定章节；若信息缺失，必须写“待补充”“未提供”或“需确认”。
- URL 必须以 `/cloudapi` 开头；若用户原始输入不符合规范，必须保留固定章节并显式标注“需确认”。

````markdown
# 接口名称

## URL
> 特别注意：保证url路径的准确性，不要自行假设
`/cloudapi/example_path`

## 请求方式
`POST`

## 参数
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| example_id | string | 是 | 示例 ID |
| page_no | integer | 否 | 页码 |

## 响应
| 字段名 | 类型 | 说明 |
|---|---|---|
| timestamp | integer | 响应时间戳，通常为毫秒级时间戳 |
| ret_code | integer | 业务返回码 |
| ret_msg | string | 返回信息 |
| data | object | 业务数据 |

### data 字段说明
| 字段名 | 类型 | 说明 |
|---|---|---|
| record_id | string | 记录 ID |
| record_name | string | 名称 |

## 示例
### 请求示例
```json
{
  "example_id": "A1001",
  "page_no": 1
}
```

### 响应示例
```json
{
  "timestamp": 1764746887924,
  "ret_code": 200000,
  "ret_msg": "",
  "data": {
    "record_id": "A1001",
    "record_name": "demo"
  }
}
```

## 异常说明
| 场景 | 说明 |
|---|---|
| 参数缺失 | 必填参数未传 |
| 参数非法 | 参数格式或取值不合法 |
| 无权限访问 | 当前调用方无访问权限 |
````

## 修改 API 说明模板

严格按以下结构输出：

- 不得调整顶层章节顺序。
- 不得删除任一固定章节；若本次未涉及，必须明确标注“未涉及”。
- URL 必须以 `/cloudapi` 开头。

````markdown
# 接口变更说明：接口名称

## 接口URL
`/cloudapi/example_path`

## 变更概述
- 本次变更涉及：[参数 / 响应 / URL / 请求方式 / 示例 / 异常说明 / 字段命名规范]
- 影响范围：[调用方 / 前端 / 测试 / 第三方接入方]

## 详细变更

### 1. URL 变更
- 变更前：`/old/path`
- 变更后：`/new/path`
- 影响说明：调用地址需同步更新

### 2. 请求参数变更
#### 2.1 新增参数
| 参数名 | 类型 | 必填 | 说明 | 影响说明 |
|---|---|---|---|---|
| source_type | string | 否 | 请求来源类型 | 老调用方可不传，新逻辑按默认值处理 |

#### 2.2 删除参数
| 参数名 | 变更前说明 | 影响说明 |
|---|---|---|
| old_biz_type | 原用于区分旧版业务类型 | 调用方需移除该字段 |

#### 2.3 参数属性调整
| 参数名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| status_code | integer，非必填 | string，必填 | 调用方需调整字段类型并保证必传 |

#### 2.4 字段命名规范调整
| 字段名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| pageNo | camelCase | page_no | 调用方请求字段命名需同步切换为 snake_case |

### 3. 响应变更
#### 3.1 顶层标准结构
| 字段名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| ret_code | 未明确 | 统一为标准响应字段 | 调用方需按标准结构解析返回结果 |

#### 3.2 新增字段
| 字段名 | 类型 | 说明 | 影响说明 |
|---|---|---|---|
| data.trace_id | string | 请求追踪 ID | 仅新增字段，不影响旧逻辑 |

#### 3.3 删除字段
| 字段名 | 变更前说明 | 影响说明 |
|---|---|---|
| data.old_status | 旧状态字段 | 依赖该字段的展示或判断逻辑需移除 |

#### 3.4 字段调整
| 字段名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| data.order_status | integer | string | 前端枚举解析逻辑需同步修改 |

### 4. 示例变更
- 变更前：未提供
- 变更后：请求示例和响应示例已按最新字段与 snake_case 规范更新

### 5. 异常说明变更
- 新增异常场景：`status_code 非法`
- 调整说明：错误提示文案由“参数错误”改为“状态值非法”

## 兼容性说明
- 是否向后兼容：否
- 升级建议：调用方上线前同步修改请求参数、字段命名方式以及响应解析逻辑
````

## 示例 1：新增 API

### 输入
创建一个查询用户积分明细接口，路径是 /member/points/details，请求方式 GET。参数有 userId，string，必填；pageNo，int，非必填；pageSize，int，非必填。返回 data 里有 total 和 list，list 里每项包括 pointId、changeType、changeValue、createdAt。异常场景包括 userId 缺失和用户不存在。

### 输出
````markdown
# 查询用户积分明细

## URL
`/cloudapi/member/points/details`

## 请求方式
`GET`

## 参数
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| user_id | string | 是 | 用户 ID |
| page_no | int | 否 | 页码 |
| page_size | int | 否 | 每页条数 |

## 响应
| 字段名 | 类型 | 说明 |
|---|---|---|
| timestamp | integer | 响应时间戳，通常为毫秒级时间戳 |
| ret_code | integer | 业务返回码 |
| ret_msg | string | 返回信息 |
| data | object | 业务数据 |

### data 字段说明
| 字段名 | 类型 | 说明 |
|---|---|---|
| total | integer | 总条数 |
| list | array | 积分明细列表 |

### list 项字段说明
| 字段名 | 类型 | 说明 |
|---|---|---|
| point_id | string | 积分明细 ID |
| change_type | string | 变更类型 |
| change_value | integer | 变更积分值 |
| created_at | string | 创建时间 |

## 示例
### 请求示例
```json
{
  "user_id": "U10001",
  "page_no": 1,
  "page_size": 20
}
```

### 响应示例
```json
{
  "timestamp": 1764746887924,
  "ret_code": 200000,
  "ret_msg": "",
  "data": {
    "total": 1,
    "list": [
      {
        "point_id": "P9001",
        "change_type": "consume",
        "change_value": -10,
        "created_at": "2026-03-23 10:00:00"
      }
    ]
  }
}
```

## 异常说明
| 场景 | 说明 |
|---|---|
| user_id 缺失 | 必填参数 user_id 未传 |
| 用户不存在 | 根据 user_id 未查询到对应用户 |
````

## 示例 2：修改 API

### 输入
把创建订单接口改一下：原来路径是 /cloudapi/order/create，现在改成 /cloudapi/trade/order/create；新增 channel 参数，string，非必填；删除 oldBizType；amount 从 int 改成 string；pageNo 改成 page_no；返回里新增 data.payToken；删除 data.oldStatus；新增异常场景 amount 非法。

### 输出
````markdown
# 接口变更说明：创建订单接口

## 接口URL
`/cloudapi/trade/order/create`

## 变更概述
- 本次变更涉及：URL、请求参数、响应、异常说明、字段命名规范
- 影响范围：前端、服务端调用方、测试

## 详细变更

### 1. URL 变更
- 变更前：`/cloudapi/order/create`
- 变更后：`/cloudapi/trade/order/create`
- 影响说明：所有调用方需更新请求地址

### 2. 请求参数变更
#### 2.1 新增参数
| 参数名 | 类型 | 必填 | 说明 | 影响说明 |
|---|---|---|---|---|
| channel | string | 否 | 下单渠道 | 老调用方可不传，新逻辑按默认渠道处理 |

#### 2.2 删除参数
| 参数名 | 变更前说明 | 影响说明 |
|---|---|---|
| old_biz_type | 原业务类型字段 | 调用方需移除该字段 |

#### 2.3 参数属性调整
| 参数名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| amount | int | string | 调用方需修改字段类型，避免类型校验失败 |

#### 2.4 字段命名规范调整
| 字段名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| pageNo | camelCase | page_no | 调用方请求字段命名需同步切换为 snake_case |

### 3. 响应变更
#### 3.1 顶层标准结构
| 字段名 | 变更前 | 变更后 | 影响说明 |
|---|---|---|---|
| timestamp / ret_code / ret_msg / data | 未统一说明 | 按标准响应结构固定输出 | 调用方需按标准结构解析响应 |

#### 3.2 新增字段
| 字段名 | 类型 | 说明 | 影响说明 |
|---|---|---|---|
| data.pay_token | string | 支付令牌 | 新增字段，不影响旧逻辑 |

#### 3.3 删除字段
| 字段名 | 变更前说明 | 影响说明 |
|---|---|---|
| data.old_status | 旧订单状态字段 | 依赖该字段的逻辑需迁移 |

### 4. 示例变更
- 变更前：未提供
- 变更后：需按最新 URL、字段命名和响应结构更新请求示例与响应示例

### 5. 异常说明变更
- 新增异常场景：`amount 非法`
- 影响说明：调用方需确保 amount 符合新格式要求

## 兼容性说明
- 是否向后兼容：否
- 升级建议：调用方需同步修改请求地址、请求参数类型、字段命名方式以及响应字段解析逻辑
````
