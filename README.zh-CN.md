# Skills

[English](./README.md) | 简体中文

个人的通用 Agent Skill 合集，主要是在各个项目里反复用到的流程类、工具类 skill。所有 skill 遵循 [Agent Skills](https://agentskills.io/specification) 规范，可以用 [skills](https://github.com/vercel-labs/skills) 命令行工具安装，并收录在 [skills.sh](https://www.skills.sh/)。

## 安装

```bash
# 安装全部 skill
npx skills add rockychang7/skills

# 只查看有哪些 skill，不安装
npx skills add rockychang7/skills --list

# 只安装某一个 skill
npx skills add rockychang7/skills --skill <skill-name>

# 更新已安装的 skill
npx skills update
```

## 现有 Skill

| Skill | 说明 |
| --- | --- |
| [rein-analyzing-requirements](./skills/rein-analyzing-requirements/SKILL.md) | 把产品需求文档变成一份对照代码检查过的底稿，再生成需求导读、后端安排、建表 SQL、上线清单、前端接口对接。需求变了，按每个读者上次收到的那版标出改动，并写好群通知。产出可选中文或英文。需要 Python 3.9 及以上（只用标准库） |

## 目录结构

```text
.
├─ skills/                    # 所有对外发布的 skill 都放这里
│  └─ <skill-name>/
│     ├─ SKILL.md             # 必须：元信息 + 说明
│     ├─ references/          # 可选：参考文档、输出模板
│     ├─ scripts/             # 可选：可执行脚本
│     └─ assets/              # 可选：静态资源
├─ template/
│  └─ SKILL.template.md       # 新建 skill 用的模板
├─ README.md
├─ README.zh-CN.md
└─ LICENSE
```

## 新增一个 Skill

1. 新建 `skills/<skill-name>/` 文件夹，把 `template/SKILL.template.md` 复制进去并改名为 `SKILL.md`。
2. 填写开头的元信息：
   - `name`：只能用小写字母、数字和单个横杠，最多 64 个字符，**必须和文件夹同名**。
   - `description`：写清楚这个 skill 做什么、什么时候用，最多 1024 个字符，带上触发关键词。
3. `SKILL.md` 尽量控制在 500 行以内，篇幅长的内容放到 `references/`。
4. 在本地确认命令行工具能识别到它：

   ```bash
   npx skills add . --list
   ```

5. 在中英文两份 README 的"现有 Skill"表格里各加一行，然后提交并推送。

仓库在 GitHub 上公开后，只要有人通过 `npx skills add rockychang7/skills` 安装，skill 就会自动出现在 [skills.sh](https://www.skills.sh/) 上。

## 开源协议

[MIT](./LICENSE)
