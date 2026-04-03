# P0 Stable Core Design

## Goal

把当前“已经能真实发布”的实验版，提升为“可稳定日常使用”的 `P0` 内核版本。

这一阶段只关注稳定性、可观测性和可恢复性，不扩展批量任务、定时发布、多账号管理等后续能力。

## Scope

本次 `P0` 只覆盖以下内容：

1. 发布前校验层
2. 三平台发布成功判定
3. 错误日志与截图归档
4. 草稿列表与发布历史
5. 审核页增强
6. 失败平台单独重试
7. 执行模式选择：自动发布或仅自动填写待人工发布

明确不在本次范围内的内容：

1. 批量发布
2. 定时发布
3. 多账号支持
4. 云端部署
5. 发布后数据抓取
6. 更复杂的 AI 建议增强

## Product Outcome

`P0` 完成后，项目应具备以下用户体验：

1. 用户先创建草稿，再在本地审核页中完成人工确认。
2. 系统在真实发布前执行结构化校验，阻止明显不合法的草稿进入发布。
3. 发布执行后，每个平台都能形成一条明确的结果记录，而不是只有“点过发布”这一动作。
4. 如果某个平台失败，用户能看到错误原因、截图和草稿上下文，并可只重试该平台。
5. 审核页首页可以浏览草稿列表，详情页可以查看平台状态与发布历史。
6. 用户可以在执行前选择两种模式：
   - 自动填写页面并自动点击发布
   - 只自动填写发布页面，最后由用户人工检查并手动点击发布

## Design Principles

### 1. Validation Before Automation

所有已知平台约束优先前置到发布前校验，而不是等页面报错后再临时处理。

### 2. Evidence Before Success

成功必须建立在“页面返回态或结果态”之上，而不是仅建立在“点击了发布按钮”之上。

### 3. One Platform Fails, Others Stay Intact

发布执行和重试都必须按平台粒度记录与恢复，不允许一个平台失败污染其他平台结果。

### 4. Human Review Remains Mandatory

本次 `P0` 不改变现有“人工确认后才允许发布”的核心安全边界。

### 5. Separate Autofill From Submit

“自动填写页面”和“自动点击最终发布”必须分开建模，允许用户在执行前主动选择模式。

## Architecture

`P0` 在现有系统上增加 6 个明确责任层：

1. `Validation`
   负责发布前校验，返回结构化校验结果。

2. `Execution Result`
   负责平台执行结果模型、日志记录和截图归档。

3. `Success Heuristics`
   负责把平台成功态定义成可复用规则。

4. `History & Retry`
   负责历史记录读取和单平台重试。

5. `Review Workspace`
   负责草稿列表、详情页状态可视化和错误可见性。

6. `Execution Mode`
   负责区分“自动发布”和“仅填充待人工发布”两种执行方式。

## Data Model Changes

### Draft Level

现有草稿模型需要扩展出与发布记录相关的数据。

建议新增这些概念：

1. `validation_status`
   - `unknown`
   - `passed`
   - `failed`

2. `validation_errors`
   - 结构化数组
   - 每项至少包含 `field`、`message`、`platforms`

3. `publish_history`
   - 按执行批次记录
   - 每次执行下再按平台拆分结果

4. `execution_mode`
   - `autopublish`
   - `autofill_only`

### Platform Publish Result

统一的发布结果对象至少应包含：

1. `platform`
2. `status`
   - `pending`
   - `running`
   - `succeeded`
   - `failed`
3. `started_at`
4. `finished_at`
5. `error_message`
6. `error_type`
7. `screenshot_path`
8. `result_url`
9. `success_signal`
10. `attempt`
11. `execution_mode`
12. `awaiting_manual_publish`

### Retry Model

单平台重试时，应明确：

1. 重试目标平台
2. 当前重试次数
3. 是否保留原失败记录

建议保留原记录，不覆盖历史，只新增一次新的执行结果。

## Validation Design

### Validation Timing

发布前校验发生在：

`draft approved`
-> `run validation`
-> `passed`
-> `fill or publish`

如果校验失败：

`draft approved`
-> `run validation`
-> `failed`
-> 阻止发布，并把错误展示到审核页

### Validation Rules

首版校验至少覆盖：

1. 视频文件存在
2. 封面文件存在
3. 已选择平台
4. 已有最终标题
5. 草稿状态已批准
6. 发布模式有效

平台特定规则至少包括：

1. 视频号短标题长度限制
2. 基础封面文件可读性
3. 平台必填项完整性

本次只要求先把已知硬限制沉淀进去，不要求一次性覆盖所有平台边界。

### Execution Mode Validation

除了草稿字段本身，还要校验执行模式：

1. 必须明确选择 `autopublish` 或 `autofill_only`
2. `autofill_only` 不能进入最终提交动作
3. 只有 `autopublish` 才参与真正的成功发布判定

## Success Heuristics Design

### Why This Is Needed

当前真实联调已经验证：平台“点发布”后，真正可靠的信号通常来自跳转后的页面状态。

因此需要把这些信号统一成代码规则，而不是散落在临时联调逻辑里。

### Two Outcome Types

本次 `P0` 需要区分两类完成态：

1. `autofill_only`
   - 目标是把页面自动填写到待人工检查与最终发布的状态
   - 这类结果必须记为 `awaiting_manual_publish`，不能记为真正发布成功

2. `autopublish`
   - 目标是完成最终点击发布并判断是否真的发布成功

### Platform Signals

建议首版规则：

1. 小红书
   - 成功信号：进入发布完成页或内容管理相关返回态

2. 抖音
   - 成功信号：进入作品管理页

3. 视频号
   - 成功信号：从创建页进入作品列表页

### Autofill-Only Signals

如果执行模式是 `autofill_only`，则每个平台都要记录“已进入待人工发布状态”的信号。

建议首版信号：

1. 小红书
   - 已上传视频，标题与正文已填入，页面停留在发布编辑页

2. 抖音
   - 已上传视频，标题与描述已填入，页面停留在发布编辑页

3. 视频号
   - 已上传视频，标题和封面已填入，页面停留在创建页待发表状态

每个平台结果记录里都要写入：

1. 命中的成功信号名称
2. 最终 URL
3. 页面状态摘要

## Error Logging Design

### What To Store

每次平台执行失败时，至少保存：

1. 草稿 ID
2. 平台名
3. 错误时间
4. 错误类型
5. 错误文案
6. 截图路径
7. 草稿快照路径

如果执行模式是 `autofill_only`，还应记录：

8. 当前页面是否已进入待人工发布态

### Why Screenshot + Snapshot

浏览器自动化的失败很大一部分来自页面结构变化、业务权限变化或未预料弹窗。只保存错误字符串通常不足以排查。

截图用于看页面状态，草稿快照用于还原输入上下文，这两者是 `P0` 可维护性的关键。

## Review Workspace Design

### Index Page

首页要从“简单入口页”升级成草稿列表页。

至少展示：

1. 草稿 ID
2. 视频文件名
3. 最近更新时间
4. 审批状态
5. 最近一次发布结果摘要

### Draft Detail Page

详情页在现有基础上新增：

1. 校验结果区域
2. 最近一次发布结果区域
3. 历史发布记录区域
4. 单平台重试入口
5. 更清晰的平台状态展示
6. 当前执行模式展示
7. “仅自动填写待人工发布”入口
8. “自动发布”入口

## Retry Design

### Retry Entry

重试入口应放在草稿详情页的发布结果区域中，按平台展示。

### Retry Behavior

点击单平台重试后：

1. 重新校验该草稿
2. 仅对目标平台执行发布
3. 生成新的平台执行记录
4. 不修改其他平台既有成功结果

重试时也必须允许重新选择执行模式：

1. `autopublish`
2. `autofill_only`

## File Responsibilities

建议按以下方式落文件：

### Existing Files To Modify

1. `src/mvpublisher/models/draft.py`
   - 增加校验状态和发布历史相关模型

2. `src/mvpublisher/approval/service.py`
   - 在批准后接入更明确的校验前置逻辑

3. `src/mvpublisher/publishers/base.py`
   - 扩展统一发布结果结构、执行模式与写盘行为

4. `src/mvpublisher/publishers/runner.py`
   - 支持平台级重试、执行模式分支与更清晰结果返回

5. `src/mvpublisher/publishers/xiaohongshu.py`
6. `src/mvpublisher/publishers/douyin.py`
7. `src/mvpublisher/publishers/wechat_channels.py`
   - 引入各自成功信号判定

8. `src/mvpublisher/storage/drafts.py`
   - 草稿与历史结果持久化

9. `src/mvpublisher/web/app.py`
   - 首页列表、详情历史、重试入口与执行模式 API

10. `src/mvpublisher/web/templates/index.html`
11. `src/mvpublisher/web/templates/draft_detail.html`
   - 运营工作台可视化增强与执行模式切换

### New Files To Consider

1. `src/mvpublisher/validation/service.py`
   - 统一发布前校验逻辑

2. `src/mvpublisher/validation/rules.py`
   - 平台规则与字段规则

3. `src/mvpublisher/history/service.py`
   - 历史记录与重试读取逻辑

4. `src/mvpublisher/execution_modes.py`
   - 执行模式枚举与语义定义

如果现有文件规模还能承受，也可以先不拆太多文件，但校验与历史至少要有明确边界。

## Testing Strategy

### Must-Have Tests

1. 校验失败时阻止发布
2. 平台成功信号被正确识别
3. 失败时能写入截图路径和错误信息
4. 单平台重试不影响其他平台结果
5. 首页列表能显示草稿摘要
6. 详情页能显示历史结果
7. `autofill_only` 不会被误记为已发布成功
8. `autopublish` 才会触发最终成功判定

### Real-World Verification

自动化测试之外，还应保留真实页面联调验证：

1. 小红书一次真实发布
2. 抖音一次真实发布
3. 视频号一次真实发布
4. 至少一次人为制造失败并验证日志与截图是否完整
5. 至少一次验证“仅自动填写待人工发布”模式

## Risks

### 1. Platform Drift

平台页面结构变化会导致成功判定和发布执行失效。

缓解方式：

1. 保留截图
2. 保留结果页面摘要
3. 把成功判定与执行逻辑拆开

### 2. Overbuilding Validation

如果在 `P0` 试图把所有平台边界都做完，会明显拖慢节奏。

缓解方式：

先沉淀已知硬限制，再在真实失败中逐步补充。

### 3. UI Scope Creep

审核页增强很容易滑向“完整产品后台”，导致 `P0` 失焦。

缓解方式：

只做列表、结果、重试、摘要，不做复杂筛选和批量操作。

## Acceptance Criteria

`P0` 完成的验收标准：

1. 未通过校验的草稿不能进入真实发布
2. 每个平台发布后都有明确结果记录
3. 失败时至少有错误信息和截图
4. 首页可以浏览草稿列表
5. 详情页可以查看平台结果与历史记录
6. 可只重试失败的平台
7. 用户可选择“自动发布”或“仅自动填写待人工发布”
8. “仅自动填写”模式不会误报为已发布成功

## Recommended Next Step

这个 spec 通过后，下一步应进入 `P0` 的实施计划拆解，只做 `P0`，不把 `P1` 混进同一轮实现里。
