# 技术规格 — History Clipboard

## 技术栈

| 层面 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.14 |
| UI 框架 | PySide6 | ^6.8 |
| 数据库 | sqlite3 | 内置 |
| 剪贴板监控 | QClipboard | 内置 |
| 系统托盘 | QSystemTrayIcon | 内置 |
| 全局快捷键 | QHotkey / registerHotKey (win32) | 内置 |
| 图片处理 | QImage / QPixmap | 内置 |
| 打包 | PyInstaller | ^6 |

## 为何弃用 Electron

Electron 在本机 Windows 11 上存在模块拦截机制故障，require('electron') 始终返回路径字符串而非 API 对象，28.x 和 33.x 两个大版本均无法工作。切换到 Python + PySide6 可消除此问题，且功能完全等价。

## 架构设计

```
┌─────────────────────────────────────────────┐
│               Main Process (Python)           │
│                                              │
│  ┌───────────────┐  ┌──────────────────┐    │
│  │ Clipboard     │  │  Database        │    │
│  │ Monitor       │  │  (sqlite3)       │    │
│  │ (QClipboard)  │  │                  │    │
│  └───────┬───────┘  └────────┬─────────┘    │
│          │                   │              │
│  ┌───────┴───────────────────┴──────────┐   │
│  │         MainWindow (QWidget)         │   │
│  │  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │SearchBar │  │  HistoryList     │  │   │
│  │  │(QLineEdit│  │  (QScrollArea +  │  │   │
│  │  │          │  │   cards)         │  │   │
│  │  └──────────┘  │  PinnedSection   │  │   │
│  │                └──────────────────┘  │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │Tray Icon │ │ Hotkey   │ │ Auto Start │  │
│  │(QSystem  │ │(Ctrl+Sh  │ │ (Registry) │  │
│  │TrayIcon) │ │ ift+V)   │ │            │  │
│  └──────────┘ └──────────┘ └────────────┘  │
└─────────────────────────────────────────────┘
```

## 数据库设计

### 数据库文件
- 位置: `{AppData}/HistoryClipboard/history.db`
- 引擎: sqlite3 (Python 内置)

### 表结构

```sql
CREATE TABLE IF NOT EXISTS history (
    id              TEXT PRIMARY KEY,          -- UUID v4
    type            TEXT NOT NULL,             -- 'text' | 'image'
    text_content    TEXT,                      -- 文字内容
    text_preview    TEXT,                      -- 前 200 字符预览
    image_path      TEXT,                      -- 图片文件相对路径
    thumbnail_path  TEXT,                      -- 缩略图相对路径
    created_at      REAL NOT NULL,             -- Unix 时间戳（秒）
    pinned          INTEGER NOT NULL DEFAULT 0,-- 0=否 1=是
    data_hash       TEXT NOT NULL,             -- SHA-256 哈希（去重）
    UNIQUE(data_hash)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_pinned ON history(pinned, created_at DESC);
```

### 去重策略
1. 捕获剪贴板内容后计算 SHA-256
2. EXISTS 检查 → 存在则 UPDATE created_at，不存在则 INSERT

## 剪贴板监控

- 方式: QClipboard.dataChanged 信号
- 无需轮询，系统主动推送变更事件
- 检测顺序: 先 image → 再 text

## 图片存储

- 位置: `{AppData}/HistoryClipboard/images/` 和 `thumbnails/`
- 缩略图: 120px 宽度等比例缩放
- 格式: PNG

## 清理调度

- QTimer 每 60 分钟触发
- 启动时立即执行一次
- 跳过 pinned=1 的记录

## 项目文件结构

```
D:\History_Clipboard\
├── CLAUDE.md
├── requirements.txt          # Python 依赖
├── main.py                   # 应用入口
├── build.spec                # PyInstaller 打包配置
│
├── docs\                     # 规范文档
├── devlog\                   # 开发日志
├── assets\                   # 图标等资源
│
└── src\
    ├── app.py                # 主应用类（窗口、托盘、生命周期）
    ├── clipboard_monitor.py  # 剪贴板监控
    ├── database.py           # sqlite3 操作
    ├── image_store.py        # 图片存取
    ├── hotkey.py             # 全局快捷键
    ├── auto_start.py          # 开机自启
    ├── scheduler.py          # 定时清理
    └── ui\
        ├── main_window.py    # 主窗口布局
        ├── history_card.py   # 单条历史卡片
        ├── history_list.py   # 历史列表
        ├── search_bar.py     # 搜索框
        ├── settings_modal.py # 设置弹窗
        └── styles.py         # 样式常量（浅蓝主题）
```
