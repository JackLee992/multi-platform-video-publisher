# 多平台视频发布工具

这是一个本地优先的多平台视频发布项目，目标是把“一条视频生成草稿、人工确认、分平台发布”整合成一套可重复使用的工作流。

当前支持的核心发布目标是：

- 小红书
- 抖音
- 视频号

项目强调两件事：

1. 尽量复用你当前已经登录的 Chrome 会话
2. 在真正发布前，保留人工确认这道安全门

## 这个项目能做什么

- 从本地视频路径创建发布草稿
- 基于视频内容生成标题、简介、封面候选建议
- 提供本地审核页面，确认最终标题、封面、平台和是否立即发布
- 统一管理三个平台的发布执行逻辑
- 在优先复用 Chrome 的前提下，保留 Playwright 兜底能力

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
./.venv/bin/python -m mvpublisher.cli serve-review
```

然后在浏览器中打开本地页面，查看草稿详情。

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

## 真实发布时的注意事项

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
