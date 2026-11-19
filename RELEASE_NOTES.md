# Stitchcraft v1.1.0 — 发布说明与交付审计

> 版本：**1.1.0** · 核心发布提交：[`5893aa3`](https://github.com/RenXiaoxiang/Stitchcraft/commit/5893aa3)
> Tag：[`v1.1.0`](https://github.com/RenXiaoxiang/Stitchcraft/tree/v1.1.0)
> 仓库：[RenXiaoxiang/Stitchcraft](https://github.com/RenXiaoxiang/Stitchcraft)
> 线上展示页：<https://renxiaoxiang.github.io/Stitchcraft/>

这份说明记录 v1.1.0 的功能范围、验证证据、第三方归属、隐私边界和已知限制。它是最终交付的一部分，不是营销页；没有真实 AI Key 时不会声称跑通了 AI benchmark，也没有把人工检查写成自动化通过。

---

## 1. 本轮交付

### 1.1 Demo 覆盖达到 5/5

五个主题全部有完整、可交互的示例站，demo 模式不再出现 placeholder：

| 主题 | 示例站 | 覆盖的交互 |
| --- | --- | --- |
| `warehouse-ops` | 仓库运营台 | 库存列表、收货、低库存、增删改、localStorage |
| `staff-directory` | Northstar People | 15 名员工、5 个部门、搜索/部门/状态筛选、员工抽屉、入职清单、增改员工 |
| `logistics-control` | Harborline Control | 12 票货运、承运商评分、搜索/状态/方式筛选、事故看板与解决、CSV 导出 |
| `personal-space` | 个人写作空间 | 文章、标签、搜索、照片墙 |
| `brand-launch` | Hollow Roast 品牌发布 | 编辑式首屏、移动端 CTA、发布节奏、预购区 |

staff/logistics 两个示例站都是原创数据与交互；人物、承运商和邮箱均为虚构（`.example`），不含真实品牌或个人信息。

### 1.2 任务取消

- 新增 `POST /api/jobs/<id>/cancel`。
- **排队任务**：立即取消、移出队列并回到终态，不占用 active slot。
- **运行任务**：设置 `cancel_requested`，在当前模型请求结束后的下一个阶段边界协作停止；staging 清理，旧项目不受影响。
- 取消是终态，不进入历史保留；队列自动推进。
- UI 提供 **Cancel build** 按钮；job id 返回前保持禁用，避免误取消上一个任务。
- 五语言主要文案已覆盖。

### 1.3 SSE 实时进度

- 服务端新增 `GET /api/jobs/<id>/events`，返回 `text/event-stream`，每次状态变化推送完整 job 快照。
- 客户端 `app/web/js/jobs.js` 通过 `fetch` + `ReadableStream` 消费 SSE：
  - 断流或浏览器不支持流时，自动回退到原有轮询；
  - 4.5 秒无帧 watchdog，避免界面永久等待；
  - 使用 `AbortController` 在任务结束时关闭连接。
- 服务端协议已切到 HTTP/1.1，浏览器与脚本客户端均验证可流式读取。
- 兼容性说明：SSE 端点仍是标准 EventSource 格式；Studio 自己使用 fetch 流式读取，以规避部分嵌入式 Chromium 对 EventSource 的异常行为。

### 1.4 前端模块化

仍保持“无框架、无构建步骤、无 CDN”，但把职责拆成模块：

```text
app/web/
├── app.js              # 编排：向导、生成、预览、历史
├── i18n.js             # 五语言 + RTL + MutationObserver
└── js/
    ├── config.js       # 阶段、provider 预设、离线主题、状态词表
    ├── jobs.js         # SSE 进度、取消、轮询回退
    └── import-site.js  # 半成品网站文件夹读取
```

`app.js` 仍负责串起工作流，但新子系统不再塞进单文件。CI 对四个前端脚本都执行 `node --check`。

### 1.5 半成品网站加工（Continue mode）

**Studio 入口**

```text
Brief → Continue an existing site → 选择网站文件夹 → Finish this site
```

**CLI 入口**

```bash
stitch refine --input ./draft-site --theme brand-launch \
  --prompt "Finish the pricing section and add a pre-order CTA" \
  --out ./.stitch/refined/home
```

实现要点：

- 接受根级 `index.html` 加文本资产：HTML/CSS/JS/JSON/SVG/TXT/MD/XML/Webmanifest。
- 自动校验：路径穿越、文件类型、重复文件、单文件大小、总大小、必须存在 `index.html`。
- 导入文件先写入 staging；AI 被要求保留已有视觉与可用内容，只返回改动文件；未改动的导入文件原样保留。
- 继续执行 `data-config.js` 注入、GSAP/库归属复制、引用完整性检查、`stitchcraft-site` marker、staging + 原子发布。
- 失败、取消或 AI 报错时，旧项目保持不变。
- Studio 上限 **80 文件 / 1 MB**；CLI 支持更大的本地文本总量。
- 二进制图片/字体流式导入被刻意排除；导入文本会发送给用户配置的 AI 服务商，README 和开发文档均明确说明这一点。

---

## 2. 验证证据

以下结果来自本地最终验证，不是推测：

```text
unittest             95 passed
validate --strict    0 errors / 0 warnings
themes verify        ok
skills verify        ok
libraries verify     ok
designs verify       ok
smoke test           PASS
benchmark (mock)     5/5 build · 0 placeholders · functional required 2/2 · strict ready
```

- **Benchmark 详情**：warehouse-inventory 与 brand-launch 的 required functional 通过；staff/logistics/personal-space 为 `untested`，按设计不计入失败，也不冒充通过。
- **Strict gate**：有本地 Obscura 时 `--strict` 退出码 0；无浏览器时 required functional 0/2、incomplete 2、退出码 1。
- **真实 UI 端到端**：Edge headless + CDP 驱动 Studio 完成一次 mock 生成，最终 `Ready`、Preview 出现 `Warehouse Operations`、九阶段全部完成、取消按钮正确隐藏。
- **SSE 端到端**：浏览器页面通过 fetch 流收到 `running → done` 两帧。
- **staff/logistics 示例**：浏览器实测搜索筛选（员工搜索 1 条、货运搜索 1 条）与页面渲染；截图人工检查通过。
- **导入路径**：`normalize_import_files` / `collect_import_files` / `POST /api/generate` 导入分支 / 生成器保留未改动文件，均有单元或 API 测试覆盖；模型调用在测试中使用 mock，没有消耗真实 Key。

CI 与 Pages：

- CI：<https://github.com/RenXiaoxiang/Stitchcraft/actions/runs/44538381042> — success
- Pages：<https://github.com/RenXiaoxiang/Stitchcraft/actions/runs/44538381004> — success
- 线上：<https://renxiaoxiang.github.io/Stitchcraft/> — HTTP 200

---

## 3. 第三方归属审计

本轮没有新增第三方依赖；`vendor/`、`skills/vendor/`、`designs/vendor/` 均未修改。

- 六个浏览器库：Fabric.js、Chart.js、SortableJS、Rough.js、Swiper、GridStack — 每个目录保留 `LICENSE`、`UPSTREAM.md`、`README.md`，`stitch libraries verify` 通过。
- 四个技能包：保留原 `LICENSE` 和 `UPSTREAM.md`，`stitch skills verify` 通过。
- 五个 DESIGN.md 设计参考：保留 MIT 原文与 attribution，`stitch designs verify` 通过。
- GSAP：Studio、仓库示例、design demo 中的每一份副本都随附 `GSAP-LICENSE.txt` + `GSAP-UPSTREAM.md`；测试会扫描所有副本。
- Obscura：Apache-2.0 runtime 按需下载，不提交二进制；license/NOTICE 文件与 `THIRD_PARTY_NOTICES.md` 保持索引。
- 新示例站没有第三方代码、没有外部 CDN、没有真实品牌素材。

---

## 4. 隐私与历史

- 当前 tracked tree 的隐私扫描：**clean** — 无真实 API key、私钥、个人邮箱、本机绝对路径。
- 示例人物、邮箱、承运商全部是虚构数据，邮箱使用 `.example` 域。
- 导入半成品时，用户选择的文本会被发送到配置的 AI 端点；这一点已写入 README 和开发文档。系统不会从导入文件读取或保存 AI/数据库凭据。
- `.gitignore` 继续覆盖 `.env*`、`*.pem`、`*.key`、本地 config、SQLite 和生成目录。
- 旧敏感内容（Devpost 私有材料、提交媒体）已从 Git 历史移除；仓库随后重建，旧提交 SHA 已不可访问。
- 当前工作区在发布后保持 clean。

---

## 5. 已知边界（诚实说明）

1. **半成品导入只支持文本资产**，Studio 1 MB / 80 文件；图片、字体等二进制文件会跳过，页面里对它们的相对引用会被引用检查标记为 warning。这是大小与安全边界，不是遗漏。
2. **取消是协作式的**：不会强行切断正在进行的模型 HTTP 请求；运行任务会在当前请求结束后停止。排队任务则立即取消。
3. **benchmark 的 required 功能只有两条**：warehouse 库存链和 brand 移动端 CTA。staff/logistics/personal-space 的浏览器场景没有被标成自动通过；它们有人工检查与静态/交互验证，但不算自动化 evidence。
4. **AI benchmark 本轮未使用真实 Key**：所有 AI 生成/导入路径的测试都 mock 了模型调用，避免消耗用户额度；真实结果取决于用户配置的 provider、模型和网络。
5. **导入文件选择器的系统级文件夹对话框没有做自动化**（浏览器安全限制）。已覆盖读取模块、API、生成器和 CLI；真实使用需要在桌面 Studio 里手动选择文件夹。
6. **SSE 的 Studio 客户端使用 fetch 流**，不是 `EventSource` 对象；服务端输出的是标准 `text/event-stream`，EventSource 客户端也可消费。这样做的原因是部分嵌入式 Chromium 会暴露 EventSource 却收不到帧。

---

## 6. 使用入口

```bash
# 安装 / 本地运行
python -m stitchcraft app

# 生成新站（mock demo）
python -m stitchcraft generate --theme staff-directory --prompt "People directory" --engine mock

# 加工半成品
python -m stitchcraft refine --input ./draft-site --theme brand-launch \
  --prompt "Finish the pricing section"

# 完整验证
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft themes verify
python -m stitchcraft skills verify
python -m stitchcraft libraries verify
python -m stitchcraft designs verify
python -m stitchcraft app --smoke-test --no-window
python -m stitchcraft benchmark --engine mock --strict
```

Studio 内的语言选择器支持中文 / English / Deutsch / العربية / Русский；阿拉伯语会整体切换 RTL。
