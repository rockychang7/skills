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
| [rein-managing-project-docs](./skills/rein-managing-project-docs/SKILL.md) | 让每个项目的文档都放在 `docs/` 下，起名都一样。项目自己的文档（`AGENTS.md`、`CLAUDE.md`、`docs/ARCHITECTURE.md`、`docs/CONVENTION.md`）固定名字和位置，需要时给出只有小节标题的骨架，并在 `AGENTS.md` 里维护"文档在哪"一小段，内容仍由你写。和 AI 一起干活产生的东西（方案、测试记录、一次性脚本和数据、页面草稿、说明页、决定记录、笔记，什么格式都行）放 `docs/process/`；提不提交由你按项目或按一组项目定，不提交的只在你这台电脑上被 git 忽略，再单向备份进私库。附带说明页、测试记录、调研三种 html 页面模板。会给 Claude Code 和 Codex 装一段简短的全局规则。需要 Node.js 18 及以上（不用装依赖） |
| [rein-writing-skills](./skills/rein-writing-skills/SKILL.md) | 用你自己的材料（反复纠正的地方、重复的步骤、出过的错）写新技能或改旧技能，只写 AI 不说就会做错的东西。动笔前先给你看设计或改动前后的对比；改技能先要一次真实出错，不往里堆内容。`skill.mjs check` 免费检查结构和写法；`run` 和 `triggers` 在临时的 Claude Code 会话里测技能，和你自己的技能、设置隔开，跟不装技能或旧版对比。需要 Node.js 18 及以上（不用装依赖），测试需要 Claude Code |

## 目录结构

```text
.
├─ skills/                    # 所有对外发布的 skill 都放这里
│  └─ <skill-name>/
│     ├─ SKILL.md             # 必须：元信息 + 说明
│     ├─ references/          # 可选：参考文档、输出模板
│     ├─ scripts/             # 可选：可执行脚本
│     └─ assets/              # 可选：静态资源
├─ README.md
├─ README.zh-CN.md
└─ LICENSE
```

## 新增一个 Skill

1. 用 [rein-writing-skills](./skills/rein-writing-skills/SKILL.md) 这个 skill 来写；或者把它带的模板
   `skills/rein-writing-skills/assets/SKILL.template.md` 复制成 `skills/<skill-name>/SKILL.md`。
   - `name`：只能用小写字母、数字和单个横杠，最多 64 个字符，**必须和文件夹同名**。
   - `description`：写清楚做什么、什么时候用、不用于什么，最多 1024 个字符。
2. 检查一遍，报错的都要改掉：

   ```bash
   node skills/rein-writing-skills/scripts/skill.mjs check skills/<skill-name>
   ```

3. 在本地确认命令行工具能识别到它：

   ```bash
   npx skills add . --list
   ```

4. 在中英文两份 README 的"现有 Skill"表格里各加一行，然后提交并推送。

仓库在 GitHub 上公开后，只要有人通过 `npx skills add rockychang7/skills` 安装，skill 就会自动出现在 [skills.sh](https://www.skills.sh/) 上。

## 开源协议

[MIT](./LICENSE)
