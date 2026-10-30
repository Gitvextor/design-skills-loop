# Design Skills Loop

**把现有 7 个 UI / UX / 动画项目串成一个循环，默认最多 6 轮。**

这是一个供编码 Agent 执行的组合 Skill。它读取原技能，按顺序修改实际工程，再查看页面、验证交互，把问题反馈给下一轮。

本仓库新增的是 **编排顺序、反馈记录、停止条件和红点参考方法**。原技能、设计资料及视频引擎来自下列作者，未改称本项目原创；本项目与各上游或红点奖无隶属、官方合作关系。

```text
frontend-design → awesome-design-md → UI UX Pro Max
        → Understand Anything → taste-skill → impeccable → kinetic-reel
        → 看实际页面、检查交互、记录问题
        ├─ 已达标：结束
        └─ 仍有问题：反馈到下一轮（最多 6 轮）
```

## 使用

需要支持读取 Skill 和修改项目的编码 Agent；准备依赖只需 Python 3.10+ 标准库。各上游若执行检索、图谱、检测器或视频编码，仍按其原说明准备 Node、浏览器、ffmpeg 等环境。

```bash
git clone https://github.com/Gitvextor/design-skills-loop.git
cd design-skills-loop
python scripts/sources.py fetch
python scripts/sources.py verify
```

在 Agent 中这样说：

> 使用这个仓库的 SKILL.md，对我的项目运行 design-skills-loop。按 7 项顺序循环，默认上限 6 轮。保留现有功能，参考红点作品的方法，逐轮查看页面、验证交互并记录结果。

已有 ZIP 缓存可用：

```bash
python scripts/sources.py fetch --cache-dir "/path/to/downloaded-zips"
python scripts/sources.py fetch --cache-dir "/path/to/downloaded-zips" --offline
```

仓库根目录就是 Skill 目录，可整体安装为 `design-skills-loop`。也可直接让 Agent 读取根目录的 [SKILL.md](SKILL.md)，无需改动全局配置。安装工具需要 GitHub 路径时，使用仓库根路径 `.`。

## 循环规则

- **默认上限 6 轮**，配置在 [loop.config.json](loop.config.json)；每轮都经过 7 个阶段。
- 目标已达到且相关验证通过时可提前停止；连续两轮没有实际改善时记录原因并结束。第 6 轮仍有问题，也要如实留下，不自动进入第 7 轮。
- 后续轮次根据问题做局部修正，保留已确认的审美方向和正常功能。
- 没有动画需求时，kinetic-reel 阶段标明不适用；有动画时，查看关键帧、转场、暂停、静音与减少动态效果。
- 每轮记录在目标工程的 `.design-loop/round-N.md`。构建通过、技能读完、审美得分都不能单独代替页面与功能验证。

循环由 Agent 按 SKILL.md 执行；Python 脚本只下载和核验依赖，**不会自行调用模型或修改你的 UI**。仓库不附带模型服务或 API 密钥，也不自动发布用户工程。

## 7 个上游

| 顺序 | 来源 | 作用 | 锁定版本许可 |
|---|---|---|---|
| 1 | [Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | 视觉方向、布局、字体 | Apache-2.0（该技能） |
| 2 | [VoltAgent awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | 品牌设计规范；它是资料库 | MIT |
| 3 | [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 交互、响应式、可访问性 | MIT |
| 4 | [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) | 组件依赖、功能与数据流 | MIT |
| 5 | [taste-skill](https://github.com/Leonxlnx/taste-skill) | 排版、比例与审美检查 | MIT |
| 6 | [impeccable](https://github.com/pbakaus/impeccable) | 界面精修与质量检查 | Apache-2.0 |
| 7 | [kinetic-reel / opus-video-skills](https://github.com/tuzhechen2005/opus-video-skills/tree/main/skills/kinetic-reel) | 动态排版、分镜、转场与配乐 | MIT；见其原版权说明 |

精确提交、ZIP SHA-256 和入口见 [sources.lock.json](sources.lock.json)。锁定版本用于复现，**不声称始终是上游最新版**。获取后保留原 LICENSE；本仓库的 MIT 仅覆盖新增编排文件，不能替换上游许可，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 红点作品怎么参考

[参考方法](references/red-dot-method.md)包含 UV Mapper、FIT Platform、BMO、AI Ad Manager 的官方链接，以及：

**找相同任务 → 观察信息与交互 → 写成具体规则 → 用真实内容实现 → 同状态截图和操作对比。**

每次参考记录“来源、观察、转化、验证”；图片观察和自己的推断分开，不能只套颜色或照搬宣传图。奖项类别按官方页面分别标注，不把所有作品统称为 Best of the Best。

## 验证

```bash
python -m unittest discover -s tests -v
python scripts/sources.py verify
```

自动测试验证依赖准备脚本的完整性、路径边界等行为；不代表执行过 6 轮 UI 改进或证明设计质量。实际项目的结果以每轮记录为准。

循环结构参考 Anthropic 的 [Workflows and feedback loops](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 和 [Evaluator-optimizer](https://www.anthropic.com/research/building-effective-agents)。
