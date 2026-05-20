---
version: alpha
name: Verdant Technical Reference
description: Calm, documentation-first visual system for API HTML pages with soft botanical neutrals, restrained green accents, dense field tables, and high-contrast code blocks.
colors:
  primary: "#17201B"
  secondary: "#65716A"
  tertiary: "#217A5B"
  neutral: "#F7F9F7"
  surface: "#FFFFFF"
  surface-soft: "#EDF3EF"
  line: "#DDE5DF"
  accent-secondary: "#245F9D"
  warning: "#9B5F14"
  code-surface: "#102019"
  code-text: "#E9F4ED"
  on-tertiary: "#FFFFFF"
typography:
  h1:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 42px
    fontWeight: 760
    lineHeight: 1.25
  h2:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 23px
    fontWeight: 720
    lineHeight: 1.25
  h3:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 17px
    fontWeight: 720
    lineHeight: 1.25
  body-md:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.65
  body-sm:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.6
  code-md:
    fontFamily: "Cascadia Code, Consolas, monospace"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.6
  label-sm:
    fontFamily: "Segoe UI, Microsoft YaHei, sans-serif"
    fontSize: 12px
    fontWeight: 700
    lineHeight: 1.2
rounded:
  sm: 8px
  md: 10px
  lg: 12px
  xl: 14px
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 10px
  lg: 14px
  xl: 18px
  xxl: 24px
  xxxl: 32px
  hero: 40px
  page: 64px
components:
  header-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.xl}"
    padding: 32px
  section-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.lg}"
    padding: 26px
  method-badge:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.full}"
    typography: "{typography.label-sm}"
    padding: 10px
  meta-tag:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.full}"
    typography: "{typography.body-sm}"
    padding: 10px
  overview-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 18px
  info-note:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 16px
  warning-note:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.warning}"
    rounded: "{rounded.sm}"
    padding: 16px
  code-block:
    backgroundColor: "{colors.code-surface}"
    textColor: "{colors.code-text}"
    rounded: "{rounded.md}"
    typography: "{typography.code-md}"
    padding: 18px
  toc-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 11px
---

# API HTML DESIGN.md

## Overview

这是一个为 API 说明页服务的文档型视觉系统。

整体气质应当安静、专业、可信，像一份经过精心排版的技术简报，而不是 Swagger 导出页、营销落地页或后台控制台。页面需要在第一眼就让读者知道接口是什么、怎么调用、哪些地方最值得注意；随后再通过稳定的分区、表格和代码块把细节层层展开。

这个系统的情绪基调是：**工程化的清晰度 + 轻微的编辑感 + 柔和的自然色调**。它既要体现技术文档的精确，也要避免传统接口文档那种生硬、拥挤、无层次的阅读体验。

## Colors

配色建立在高可读性的深色正文、低刺激浅色背景和单一主强调色之上。

- **Primary (`#17201B`)**：深墨绿色黑，用于主标题、正文关键内容和核心文本。它承担页面主要信息密度，必须保持稳定、克制、可信。
- **Secondary (`#65716A`)**：灰绿中性色，用于辅助说明、标签文字、次级说明和弱化信息。它负责把正文与注释、摘要信息区分开。
- **Tertiary (`#217A5B`)**：克制的植物绿色，是页面最主要的交互和强调色。方法标签、重点提示边框、少量强调元素都应优先使用它。
- **Neutral (`#F7F9F7`)**：极浅的纸面底色，带轻微绿色倾向，营造柔和、干净的阅读环境，比纯白更像正式文档纸面。
- **Surface (`#FFFFFF`)**：白色面板底，用于头部摘要区、正文 section、信息卡片和表格容器。它是信息承载层。
- **Surface Soft (`#EDF3EF`)**：柔和浅绿色表面，用于 note、次级强调区和低风险提示块。
- **Line (`#DDE5DF`)**：浅灰绿色边框，用于卡片、表格、目录按钮和区块边界。它必须轻，但要稳定存在。
- **Accent Secondary (`#245F9D`)**：冷静的技术蓝，只用于字段名、技术型强调和局部结构识别，不应与主强调色争夺主导权。
- **Warning (`#9B5F14`)**：暖棕橙，用于 warning 提示和风险说明。它只在需要引起注意时使用。
- **Code Surface (`#102019`)** 与 **Code Text (`#E9F4ED`)**：用于代码块，形成高对比的暗色阅读区，让请求和响应示例在页面中自然形成“技术事实层”。

整个页面应避免多主色并存。除了主绿色和少量技术蓝、warning 色外，不应再引入额外高饱和强调色。

## Typography

排版策略服务于“长文可读”和“技术信息可辨”。

- 标题与正文使用人文感较强的系统无衬线字体，以保证中文与英文混排时的稳定性和现代感。
- 字段名、类型、路径、代码、状态值必须使用等宽字体，让技术信息在表格与代码块中保持识别度。
- **H1** 需要有足够重量和尺寸，用于建立页面的唯一主标题，不需要任何额外装饰。
- **H2 / H3** 用于建立正文层级，必须明显区分，但不能破坏整体文档感。
- 正文字号与行高要适合连续阅读，避免接口说明看起来像紧凑日志。
- 标签和方法徽标使用小号、较高字重的样式，以形成摘要信息层。

本系统的排版重点不是“品牌个性”，而是“高密度信息下仍然能快速扫描并保持舒适阅读”。

## Layout

布局采用文档型中心列结构，而不是应用界面式铺满布局。

- 页面主体应居中，宽度控制在适合长文阅读的范围内，避免整屏摊开。
- 顶部摘要区在桌面端可使用“主内容 + 摘要标签”双列布局，在移动端必须切换成单列。
- 正文采用 section-by-section 的展开方式，每个 section 都应像独立的信息面板。
- 卡片区适合做快速概览，通常为 2 到 4 张卡，不宜过多。
- 表格是主要信息承载方式，但复杂结构必须拆表，而不是一张总表塞完全部字段。
- 目录导航用于加快跳转，应位于头部之后、正文之前。

空间节奏采用明确但克制的间距等级：小间距服务标签、按钮和表头；中间距服务段落和组件；大间距服务主区块之间的呼吸感。

## Elevation & Depth

深度表达必须轻量。

这个系统不依赖厚重阴影或强烈浮层效果，而是通过以下方式表达层次：

- 浅背景与白色 surface 的对比
- 轻边框分隔内容区域
- 柔和阴影提升重要面板，如头部摘要区
- 局部半透明或轻微磨砂感用于强化头部的“摘要面板”属性

深度的目标是帮助用户理解信息分层，而不是制造夸张的视觉戏剧性。

## Shapes

形态语言应当柔和、克制、工程化。

- 主体面板、区块、表格容器、卡片统一使用 8px 到 14px 的圆角范围。
- 方法标签、状态标签、摘要标签采用 pill 形态，强调“可扫读的属性块”。
- 不使用完全锐利的直角，也不使用过大的圆润卡通圆角。

整体形态应给人“被整理过的技术文档”感，而不是“玩具感组件库”或“品牌营销模块”。

## Components

本设计系统的关键组件如下：

- **Header Panel**：页面的身份区，负责承载标题、简介、方法和路径，是最重要的信息入口。
- **Method Badge**：用于快速识别 `GET`、`POST` 等请求方式，必须醒目但不喧宾夺主。
- **Meta Tag**：用于展示认证方式、请求体类型、返回类型、更新时间等摘要属性。
- **TOC Chip**：目录导航项，负责快速跳转主要章节，应轻量、整齐、可横向换行。
- **Overview Card**：用于概括 2 到 4 个关键事实，例如认证来源、数据来源、变更重点、特殊业务限制。
- **Info Note / Warning Note**：用于说明特殊规则、兼容性影响、字段来源或风险说明。warning 的语义必须明显强于普通 note。
- **Data Table**：用于字段解释，是页面的核心组件。字段表必须可扫读、可横向滚动、适合拆层说明。
- **Status Table**：用于状态码、错误码、返回状态解释，语义上独立于字段表。
- **Code Block**：用于请求和响应示例，应形成深色技术层，与正文说明区明显区分。
- **Marker / Pill**：用于标注新增字段、可选字段、特殊状态等，不应过度使用。

新增 API 页面中，组件更偏完整说明；修改 API 页面中，组件更偏变更对照和影响提示。

## Do's and Don'ts

- Do 先让读者看懂接口的身份、用途和调用方式，再展开字段细节。
- Do 把复杂响应结构拆成多个逻辑清晰的表，而不是堆成一张超长表。
- Do 使用等宽字体展示路径、字段名、类型和代码内容。
- Do 让 note 和 warning 明确区分，避免风险提示被普通说明淹没。
- Do 在修改 API 页面中聚焦“改了什么”和“影响什么”。
- Do 保持一套稳定的绿色文档型视觉语言，不要每个页面都换风格。
- Don't 做成 Swagger 自动导出的原始技术页面。
- Don't 做成营销页、海报页、活动页或 dashboard 风格。
- Don't 使用多主色、强渐变、重阴影或大面积高饱和色块。
- Don't 让目录、卡片、表格、代码块在视觉上像来自不同系统。
- Don't 为了“完整”而在变更说明页里重写整份未变化接口文档。
- Don't 把字段说明、风险说明和示例内容混在一个区块中。
