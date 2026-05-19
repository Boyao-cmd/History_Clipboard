# History Clipboard — AI 工作指引

一款 Windows 桌面历史剪贴板管理软件。自动记录用户复制的内容（文字+图片），提供历史查看、搜索、置顶、重新粘贴等功能。

- **技术栈**: Python 3 + PySide6 + sqlite3
- **入口文件**: [main.py](main.py)

## 规范文件索引

| 文件 | 内容 | 何时查阅 |
|------|------|---------|
| [docs/requirements.md](docs/requirements.md) | 用户需求文档 | 开始新功能前 |
| [docs/tech-spec.md](docs/tech-spec.md) | 技术规格，架构、数据库、组件设计 | 写后端代码前 |
| [docs/design-spec.md](docs/design-spec.md) | 设计规范，配色、组件、布局 | 写前端 UI 前 |
| [docs/dev-steps.md](docs/dev-steps.md) | 开发执行步骤 | 规划具体任务前 |
| [docs/testing-checklist.md](docs/testing-checklist.md) | 测试检查清单 | 每个阶段验收前 |

## 开发工作流

1. **先读规范** — 根据任务类型阅读对应的 docs/ 文件
2. **检查 devlog** — 查看 devlog/ 下最新日期的日志，了解当前进度
3. **按阶段推进** — 一次只做一个阶段，完成 + 验证后再进入下一阶段
4. **写日志** — 每次开发会话在 devlog/ 下创建 `YYYY-MM-DD.md`
5. **验证** — 对照 testing-checklist.md 确认通过再进入下一阶段

## 启动方式

```bash
# 开发运行
python main.py

# 打包为 .exe
pyinstaller build.spec
```

## 日志机制

- 每次开发会话时检查 `devlog/` 是否有今天的 `YYYY-MM-DD.md`
- 没有则创建，有则更新
- 记录：会话目标、已完成、待办、遇到的问题、下一步计划
