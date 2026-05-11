---
name: cunxin-sql-schema-generator
description: Generate MySQL SQL schema reference files for this project using Cunxin rules. Use this skill when the task requires creating SQL schema, DDL, create table statements, index definitions, or database structure reference documents.
---

# Cunxin SQL Schema Generator

本 Skill 用于在当前项目中生成 SQL schema 参考产物，例如建表语句、DDL、索引定义和字段结构说明。

## 适用场景

在以下场景中必须使用本 Skill：

- 需要生成新的 MySQL 建表语句
- 需要生成 schema 参考文件
- 需要输出 SQL DDL 作为设计产物或交付产物
- 需要为 `../../../docs/generated/<work_id>/sql/` 生成 SQL schema 文件

## 强制规则

- 所有表都必须包含以下公共字段：

```sql
`uidpk` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'uidpk',
`is_del` tinyint(1) NOT NULL DEFAULT '0' COMMENT '删除标识',
`create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
`update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
```

- 所有表必须统一使用以下存储配置：

```sql
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
```

- 每个字段只要支持默认值，就必须显式设置默认值。
- 主键字段必须使用 `uidpk bigint unsigned NOT NULL AUTO_INCREMENT`。
- 必须为表和字段补充明确的 `COMMENT`。
- 布尔语义字段默认使用 `tinyint(1)`，并显式设置默认值。
- 删除标识统一使用 `is_del tinyint(1) NOT NULL DEFAULT '0'`。
- 创建时间和更新时间字段定义必须与本 Skill 的统一模板保持一致。

## 命名与输出规则

- 所有业务表名必须以 `alive_lp_` 开头，后接清晰、稳定的业务语义名称，使用下划线命名法。
- 如果用户给出的表名不符合 `alive_lp_` 前缀规则，必须先指出问题并确认是否按项目规范修正。
- 生成的 SQL schema 属于参考产物，应输出到 `../../../docs/generated/<work_id>/sql/`。
- 文件名应尽量表达业务含义，例如：
  - `position-schema.sql`
  - `album-schema.sql`
  - `order-schema.sql`
- 若一个任务需要生成多个表，可放在同一个 `.sql` 文件中，也可按业务拆分多个文件，但都必须位于同一个 `work_id` 目录下。

## 生成步骤

1. 确认表的业务语义、表名、字段名、字段类型和索引需求。
2. 检查字段是否都具备合理默认值。
3. 补齐统一公共字段。
4. 补齐主键、索引、注释和表注释。
5. 统一追加 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci`。
6. 将最终产物输出到 `../../../docs/generated/<work_id>/sql/`。

## 标准模板

```sql
CREATE TABLE `alive_lp_table_name` (
  `uidpk` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'uidpk',
  `field_a` varchar(128) COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '字段A',
  `field_b` int NOT NULL DEFAULT '0' COMMENT '字段B',
  `is_del` tinyint(1) NOT NULL DEFAULT '0' COMMENT '删除标识',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`uidpk`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='表说明';
```

## 参考示例

以下结构是当前项目的参考风格：

```sql
CREATE TABLE `alive_lp_global_position` (
  `uidpk` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'pk',
  `flg_active` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否启用:0-未启用 1-启用',
  `position_name` varchar(128) COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '点位名称',
  `paid_mode` int NOT NULL DEFAULT '3' COMMENT '收费模式:1-先拍后买 2-旅拍套餐 3-免费下载',
  `package_id` bigint NOT NULL DEFAULT '0' COMMENT '套餐ID（先拍后买取这个值）',
  `package_name` varchar(128) COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '套餐名字（先拍后买取这个值）',
  `template_id` bigint NOT NULL DEFAULT '0' COMMENT '拍摄模式ID',
  `template_name` varchar(128) COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '拍摄模式名称',
  `customer_id` bigint NOT NULL DEFAULT '0' COMMENT '用户ID',
  `watermark_enable` tinyint(1) NOT NULL DEFAULT '0' COMMENT '点位下水印的开关',
  `is_del` tinyint(1) NOT NULL DEFAULT '0' COMMENT '删除标识',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`uidpk`),
  KEY `idx_customer_id` (`customer_id`) COMMENT '用户ID索引',
  KEY `idx_flg_active` (`flg_active`) COMMENT '是否启用索引'
) ENGINE=InnoDB AUTO_INCREMENT=32482 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='全局点位';
```

## 禁止事项

- 不要遗漏统一公共字段。
- 不要省略字段默认值（在字段支持默认值的前提下）。
- 不要生成不符合 `alive_lp_` 前缀规则的业务表名，除非用户明确要求并确认偏离规范。
- 不要使用非 `InnoDB` 引擎。
- 不要使用与项目不一致的字符集或排序规则。
- 不要输出无注释的表或字段。
- 不要将生成结果写到 `../../../docs/generated/<work_id>/sql/` 之外的目录，除非用户明确要求。
