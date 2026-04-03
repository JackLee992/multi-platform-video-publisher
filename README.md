# 多平台视频发布工具

这是一个本地优先的多平台视频发布项目，目标是把“一条视频生成草稿、人工确认、分平台发布”整合成一套可重复使用的工作流。

当前支持的核心发布目标是：

- 小红书
- 抖音
- 视频号

项目强调两件事：

1. 尽量复用你当前已经登录的 Chrome 会话
2. 在真正发布前，保留人工确认这道安全门

当前推荐的默认使用约定是：

1. 默认走“标准流程”
   - 创建草稿
   - 打开审核页
   - 人工确认
   - 再执行发布
2. 只有做回归测试、重复模板验证，或者你明确要“直接按模板发”时，才走 Chrome 当前会话脚本

## 这个项目能做什么

- 从本地视频路径创建发布草稿
- 基于视频内容生成标题、简介、封面候选建议
- 提供本地审核页面，确认最终标题、封面、平台和是否立即发布
- 支持两种执行模式
  - `autofill_only`：只自动填写到待人工发布状态
  - `autopublish`：自动填写后继续提交发布
- 统一管理三个平台的发布执行逻辑
- 在优先复用 Chrome 的前提下，保留 Playwright 兜底能力
- 记录发布历史、结果摘要和草稿快照
- 支持单平台重试

## 当前仓库包含什么

这个仓库只包含代码、模板和测试，不包含任何真实素材或运行产物。

仓库明确排除了这些内容：

- 原始视频
- 抽帧封面图
- 运行时草稿
- 发布日志和截图
- 浏览器登录资料
- 本地虚拟环境

也就是说，推送到 GitHub 的是“工具本身”，不是“你的内容资产”。

## 适合怎么用

这个项目适合这样的场景：

- 你经常需要把同一条视频发到多个平台
- 你希望先自动生成建议，再人工确认后发布
- 你更希望继续使用当前 Chrome 的登录状态，而不是每次重新登录
- 你希望后续继续扩展平台、字段校验或自动化流程

如果你想要“完全无人值守、云端定时、规避平台风控”的系统，这个仓库还不是那个方向。它更适合本地运营助手，而不是黑盒机器人。

## 环境准备

建议环境：

- macOS
- Python 3.11 及以上
- 已安装并可正常使用的 Google Chrome
- 目标平台账号已经在 Chrome 里登录

初始化方式：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

如果后续需要 Playwright 兜底，可以额外安装浏览器运行时：

```bash
python -m playwright install chromium
```

## 首次使用前必须确认的权限

第一次在本机跑真实发布前，除了安装依赖，还需要确认系统权限和浏览器权限已经放开。

### 1. macOS 系统权限

如果你是通过 Codex、终端脚本、AppleScript 或系统事件去驱动 Chrome，通常至少会遇到这些授权项：

- 辅助功能权限
  用于模拟点击、键盘输入、切换窗口和操作系统文件选择器
- 自动化权限
  用于允许当前终端或代理控制 `Google Chrome`、`System Events` 等应用
- 文件与文件夹访问权限
  用于读取本地视频、封面图和运行时目录
- 屏幕录制权限
  某些情况下不是硬性必需，但如果你后续要做界面识别、截图校验或录屏排查，建议提前开启

如果这些权限没有打开，常见表现会是：

- 浏览器标签页能打开，但按钮点击没有效果
- 文件选择器没有反应
- 系统键盘输入失败
- AppleScript 提示没有权限控制 Chrome 或 System Events

### 2. Chrome 浏览器侧权限

建议首次使用前确认：

- Chrome 已登录目标平台账号
- Chrome 没有处于访客模式或临时无痕窗口
- 平台站点允许正常使用 Cookie
- 没有被浏览器插件拦截关键页面脚本

如果你要尽量复用当前 Chrome 登录态，建议：

- 直接在你平时使用的 Chrome 个人资料里登录三个平台
- 打开过一次各自的创作者后台页面
- 不要在执行过程中频繁切换到退出登录、清理 Cookie、禁用脚本的状态

### 3. 网页或平台站点内的权限提示

部分平台在首次进入创作者后台或首次发布时，可能还会再弹自己的授权或提示框，例如：

- 允许上传文件
- 允许读取剪贴板
- 风险提示确认
- 管理员验证或扫码确认
- 绑定运营者、绑定店铺、绑定视频号主体等业务权限确认

这些提示不一定都能绕过，建议的处理方式是：

1. 先人工确认一次
2. 记录提示文案和页面状态
3. 再决定是否把它沉淀成自动化分支逻辑

### 4. 首次真实发布前的建议检查清单

建议至少手工确认一次下面这些条件：

1. 当前终端或代理已有 macOS 辅助功能和自动化权限
2. Chrome 中已登录小红书、抖音、视频号
3. 三个平台的创作者后台页面都能正常打开
4. 本地视频路径可读
5. 本地封面路径可读
6. 没有系统弹窗正在等待人工确认

## 先验证项目是否可用

安装完成后，先跑完整测试：

```bash
./.venv/bin/python -m pytest -q
```

如果测试通过，再进入真实素材流程。

## 标准使用流程

### 1. 准备视频

你需要先准备一个本地视频文件路径，例如：

```bash
/absolute/path/to/video.mov
```

建议先用非敏感测试视频把流程跑通，再换正式素材。

### 2. 创建发布草稿

执行：

```bash
./.venv/bin/python -m mvpublisher.cli create-draft /absolute/path/to/video.mov
```

这一步会做几件事：

- 创建草稿数据
- 调用视频理解能力生成标题和简介建议
- 抽取封面候选图
- 准备后续审核页需要的运行时文件

### 3. 打开本地审核页

执行：

```bash
./.venv/bin/python -m mvpublisher.cli serve-review <draft-id>
```

命令会默认用 `Google Chrome` 打开本地审核页。

审核阶段建议你重点确认：

- 视频文件是否正确
- 最终标题是否满足平台限制
- 封面是否合适
- 勾选的平台是否正确
- 是否立即发布

### 4. 进行人工确认

审核页当前支持：

- 从系统生成的候选封面中直接选择
- 上传你自己的最终封面图
- 选择最终标题
- 选择发布平台
- 选择执行模式
  - `autofill_only`
  - `autopublish`
- 查看校验结果
- 查看发布历史
- 对单个平台发起重试

只有草稿进入批准状态后，才应该进入发布执行。

### 5. 执行发布

执行：

```bash
./.venv/bin/python -m mvpublisher.cli publish-draft <draft-id>
```

发布阶段的策略是：

1. 优先尝试复用当前 Chrome 会话
2. 如果无法复用，再考虑 Playwright 持久态
3. 发布完成后，根据页面跳转或结果页状态判断是否成功

如果你希望继续留在审核页里完成执行，也可以直接在草稿确认页里点 `保存并执行`：

- 点击 `保存并执行`
- 页面会先保存当前审核结果，再立即开始执行
- 执行控制台会轮询显示当前执行状态、日志和每个平台结果

这条路径更适合日常使用标准流程，因为审核和执行都保留在同一个页面里。

### 两种执行模式的区别

#### 1. `autofill_only`

这个模式下，系统会：

- 打开目标平台页面
- 尽可能自动完成页面填写
- 停留在待人工检查和手动点击发布的状态

这个模式不会把结果记为“已发布成功”，而是记为：

- `awaiting_manual_publish`

适合这些情况：

- 你想最后再人工看一遍页面
- 平台风控比较敏感
- 你暂时只想做半自动工作流

#### 2. `autopublish`

这个模式下，系统会：

- 自动填写页面
- 尝试继续执行最终提交动作

当前仓库已经把这个模式正式建模进数据结构和工作流里，但你仍然应该把“是否真的发布成功”建立在页面结果信号上，而不是只看有没有发起提交。

## 真实发布时的注意事项

### Chrome 当前会话注入脚本

如果你已经在当前 Chrome 里登录了三个平台，而且希望尽量复用“当前标签页 + JS 注入”的方式，可以直接使用仓库里的脚本：

```bash
./scripts/chrome_current_session_publish.sh \
  --video /absolute/path/to/video.mov \
  --cover /absolute/path/to/cover.jpg \
  --title "第二次三端测试"
```

这个脚本会：

- 复用当前 Chrome 已打开的平台发布页
- 如果目标发布页没开，会主动补开
- 在执行前主动把 Chrome 和目标平台标签页切到前台
- 在本地启动或复用一个文件服务
- 通过 AppleScript 向当前页面注入 JS
- 把本地视频包装成 `File` 并塞进页面的 `input[type=file]`
- 自动填写标题、正文，并在部分平台执行封面动作
- 默认继续点击最终发布

如果你只想走到“已上传并已填字段”，不立即提交，可以加：

```bash
./scripts/chrome_current_session_publish.sh \
  --video /absolute/path/to/video.mov \
  --cover /absolute/path/to/cover.jpg \
  --title "第二次三端测试" \
  --skip-publish
```

如果只想测试单个平台：

```bash
./scripts/chrome_current_session_publish.sh \
  --video /absolute/path/to/video.mov \
  --cover /absolute/path/to/cover.jpg \
  --title "第二次三端测试" \
  --platform xiaohongshu
```

### 当前已真机验证通过的脚本路径

下面这些结论都来自当前 Chrome 会话的真实联调，不是只看代码推断：

- 小红书
  - 视频上传：已验证
  - 标题填入：已验证
  - 正文填入：已验证
  - 封面动作：已验证
    当前走“智能推荐封面/平台内封面动作”这条稳定路径
- 抖音
  - 视频上传：已验证
  - 标题填入：已验证
  - 正文填入：已验证
- 视频号
  - 视频上传：已验证
  - 短标题填入：已验证
  - 正文填入：已验证
  - 封面上传动作：已验证

### 当前还没有完全打满的边界

虽然三平台都已经能进编辑页并完成关键字段填入，但 README 这里需要明确说清楚，当前还不是“所有字段、所有平台、所有分支都 100% 产品化”的终态。

- 小红书
  - 当前封面更稳定的是“平台内推荐/默认封面动作”
  - 还没有把“严格自定义图片上传封面”做成稳定默认路径
- 抖音
  - 当前标题/正文稳定
  - 封面自动化还没有像正文一样做完整回读校验
- 视频号
  - 封面上传动作已经验证通过
  - 但还建议继续补“页面回读确认封面最终替换成功”的校验
- 三平台共同
  - 标准流程审核页里的执行控制台已可用
  - 但步骤状态还可以继续细化成更强的可视调试面板

### 当前推荐的使用建议

- 日常正式使用
  优先走审核页标准流程，在页面里确认标题、封面、平台和执行模式后，再点“保存并执行”
- 快速联调或脚本回归
  直接使用 `scripts/chrome_current_session_publish.sh`
- 对“是否真的发布成功”的判断
  仍然要结合页面结果信号，而不是只看脚本返回值

补充说明见：
[chrome-current-session-injection.md](/Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher/docs/chrome-current-session-injection.md)

### Chrome 登录态

如果你希望流程尽量顺畅：

- 先在 Chrome 里登录小红书、抖音、视频号
- 尽量保持创作者后台页面可访问
- 避免在执行过程中手动切走重要页面

### 平台差异

不同平台会有不同限制，当前已经明确验证过的一个例子是：

- 视频号短标题不能超过 16 个中文字符

这类限制后续应该继续沉淀进发布前校验，而不是等页面报错后再人工处理。

### 成功判定

浏览器自动化里，“点击了发布”不等于“已经成功发布”。

更可靠的判断方式是：

- 小红书：跳回发布完成页或内容管理相关页面
- 抖音：跳到作品管理页
- 视频号：从创建页跳到作品列表页

建议把“页面结果校验”当成发布器的一部分长期维护。

### 发布结果与运行产物

每次执行后，系统会在运行目录里保留与该次发布有关的文件，典型包括：

- `publish_result.json`
- `result_summary.txt`
- `page_state.txt`
- 草稿快照文件

这些文件不会提交到 GitHub，但会保留在本地，方便你排查问题和回看执行上下文。

### 单平台重试

如果一次执行里只有某个平台失败，不需要整条任务重跑。

当前支持的做法是：

1. 在审核页查看历史结果
2. 选择目标平台
3. 指定执行模式
4. 仅对该平台重试

重试不会覆盖旧记录，而是追加一条新的执行历史。

## 常用命令

创建草稿：

```bash
./.venv/bin/python -m mvpublisher.cli create-draft /absolute/path/to/video.mov
```

启动审核服务：

```bash
./.venv/bin/python -m mvpublisher.cli serve-review
```

发布已批准草稿：

```bash
./.venv/bin/python -m mvpublisher.cli publish-draft <draft-id>
```

查看 CLI 帮助：

```bash
./.venv/bin/python -m mvpublisher.cli --help
```

## 项目结构

```text
src/mvpublisher/
  approval/      # 审批与最终确认
  media/         # 视频处理、抽帧、技能适配
  models/        # 草稿模型与平台字段
  publishers/    # 平台发布器与统一 runner
  sessions/      # Chrome 复用与 Playwright 兜底
  storage/       # 草稿持久化
  suggestions/   # 标题、简介、封面建议生成
  web/           # 本地审核页面
  workflows.py   # 端到端草稿工作流
tests/           # 自动化测试
```

## 如果要继续扩展，应该怎么改

### 1. 想新增平台

优先看这里：

- `src/mvpublisher/publishers/`
- `src/mvpublisher/models/draft.py`
- `src/mvpublisher/publishers/runner.py`

建议做法：

1. 增加新的平台枚举和平台草稿字段
2. 新增一个平台发布器
3. 把它注册到统一 runner
4. 补最小测试，先验证调度，再验证页面逻辑

### 2. 想新增审核字段

优先看这里：

- `src/mvpublisher/models/draft.py`
- `src/mvpublisher/approval/service.py`
- `src/mvpublisher/web/app.py`
- `src/mvpublisher/web/templates/draft_detail.html`

适合新增的字段包括：

- 分平台标题
- 标签
- 话题
- 定时发布时间
- 分平台描述

### 3. 想优化建议生成

优先看这里：

- `src/mvpublisher/media/video_skill_adapter.py`
- `src/mvpublisher/suggestions/generator.py`
- `src/mvpublisher/media/cover_frames.py`

你可以继续增强：

- 标题候选质量
- 封面文案建议
- 关键帧挑选策略
- 不同平台的文案改写逻辑

### 4. 想优化浏览器自动化

优先看这里：

- `src/mvpublisher/sessions/browser_reuse.py`
- `src/mvpublisher/sessions/playwright_fallback.py`
- `src/mvpublisher/publishers/xiaohongshu.py`
- `src/mvpublisher/publishers/douyin.py`
- `src/mvpublisher/publishers/wechat_channels.py`

建议重点维护：

- 页面选择器稳定性
- 上传动作可靠性
- 弹窗识别
- 成功判定逻辑
- 平台限制校验前置

### 5. 想做更完整的产品化界面

优先看这里：

- `src/mvpublisher/web/templates/index.html`
- `src/mvpublisher/web/templates/draft_detail.html`
- `src/mvpublisher/web/app.py`

可以继续加：

- 更完整的封面预览区
- 分平台字段区分
- 草稿列表筛选
- 发布历史查看
- 错误回放和截图预览

## 后续开发建议

如果你要继续把它做成长期可维护项目，我建议优先级按这个顺序走：

1. 固化平台限制校验，减少发布时才报错
2. 把“成功判定”做得更明确，不只依赖点击动作
3. 给每个平台补更多真实页面回归测试
4. 优化审核页体验，让运营确认更顺手
5. 再考虑批量发布、定时发布、多账号管理

## 配套资源

- 项目仓库：<https://github.com/JackLee992/multi-platform-video-publisher>
- 配套 skill 仓库：<https://github.com/JackLee992/multi-platform-video-publisher-skill>

如果你是在 Codex 里配合这个项目使用，建议同时安装配套 skill，这样后续让代理继续维护会更顺。
