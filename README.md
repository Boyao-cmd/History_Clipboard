# History Clipboard

一款 Windows 桌面历史剪贴板管理软件。在后台自动记录你复制的文字和图片，随时查看、搜索、置顶，并一键重新粘贴到任何应用。

## 功能特性

- **自动记录** — 后台监控系统剪贴板，复制文字或图片时自动存入历史（检测延迟 < 500ms）
- **智能去重** — 连续复制相同内容不产生重复记录，而是将其时间戳更新到最新
- **历史列表** — 卡片式展示，文字显示前 200 字符预览，图片显示缩略图，附带相对时间（如"2 分钟前"）
- **实时搜索** — 输入即过滤文字记录（防抖 200ms）
- **置顶** — 将常用记录固定在列表顶部独立分区，置顶记录不受自动清理影响
- **一键回贴** — 点击复制按钮将内容写回系统剪贴板，Ctrl+V 即可粘贴到任意应用
- **自动清理** — 可设置保留天数（1 / 3 / 5 天，默认 3 天），启动时及每小时自动清理过期记录
- **后台常驻** — 最小化到系统托盘，双击托盘图标打开窗口
- **全局快捷键** — 任意界面按 `Ctrl+Shift+V` 呼出 / 隐藏窗口
- **开机自启** — 默认注册到 Windows 启动项
- **隐私安全** — 所有数据仅保存在本地，不上传任何服务器

## 技术栈

| 层面 | 技术 |
|------|------|
| 语言 | Python 3.14 |
| UI 框架 | PySide6 (Qt for Python) |
| 数据库 | sqlite3（内置） |
| 剪贴板监控 | QClipboard `dataChanged` 信号（事件驱动，无轮询） |
| 系统托盘 | QSystemTrayIcon |
| 全局快捷键 | win32 `RegisterHotKey` |
| 打包 | PyInstaller |

> 最初采用 Electron 方案，因 Windows 11 环境下 Electron 模块加载存在故障而改用 Python + PySide6，功能完全等价。

## 快速开始

### 环境要求

- Windows 10 / 11
- Python 3.10+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 开发运行

```bash
python main.py
```

### 打包为 .exe

```bash
pyinstaller build.spec
```

生成的单文件可执行程序位于 `dist/HistoryClipboard.exe`。

## 项目结构

```
History_Clipboard/
├── main.py                   # 应用入口（主窗口 UI 与逻辑）
├── requirements.txt          # Python 依赖
├── build.spec                # PyInstaller 打包配置
├── CLAUDE.md                 # AI 协作工作指引
│
├── src/
│   ├── database.py           # sqlite3 数据操作
│   ├── clipboard_monitor.py  # 剪贴板监控（含防抖、微信图片兼容处理）
│   ├── image_store.py        # 图片与缩略图存取
│   ├── tray.py               # 系统托盘
│   ├── hotkey.py             # 全局快捷键 Ctrl+Shift+V
│   ├── auto_start.py         # 开机自启（注册表）
│   └── scheduler.py          # 过期记录定时清理
│
├── docs/                     # 规范文档
│   ├── requirements.md       # 需求文档
│   ├── tech-spec.md          # 技术规格（架构、数据库设计）
│   ├── design-spec.md        # 设计规范（配色、组件、布局）
│   ├── dev-steps.md          # 开发执行步骤
│   └── testing-checklist.md  # 测试检查清单
│
├── devlog/                   # 开发日志
└── assets/                   # 图标、字体等资源
```

## 数据存储

- 数据库：`%APPDATA%/HistoryClipboard/history.db`（sqlite3）
- 图片文件：`%APPDATA%/HistoryClipboard/images/`（原图）与 `thumbnails/`（120px 缩略图）
- 去重方式：内容 SHA-256 哈希，唯一索引保证不重复

所有数据仅存储在本地，重启电脑后历史记录不丢失。

## 文档

| 文档 | 内容 |
|------|------|
| [需求文档](docs/requirements.md) | 功能需求（FR-01 ~ FR-12）与非功能需求 |
| [技术规格](docs/tech-spec.md) | 架构设计、数据库表结构、模块划分 |
| [设计规范](docs/design-spec.md) | 浅蓝主题配色、字体、组件与布局规范 |
| [测试清单](docs/testing-checklist.md) | 各阶段验收标准 |

## 许可证

个人项目，未指定开源许可证。
