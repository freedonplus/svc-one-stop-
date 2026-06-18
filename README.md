# OneStopService — 本地服务一条龙管理

> 一个基于 Web 的本地开发环境服务管理器，让你告别多个终端窗口的烦恼。

通过美观、直观的 Web 界面一站式管理本地开发环境中的各类服务 —— **MySQL、Redis、RabbitMQ、Nacos、Sentinel、ZipKin** 等。支持服务的启动/停止、批量操作、实时日志查看、端口检测，以及服务配置的 CRUD 管理。

---

## 界面一览

```
┌─────────────────────────────────────────────────────────┐
│  OneStopService                 搜索服务...  [+ 新增]   │
├─────────────────────────────────────────────────────────┤
│  数据库                                                  │
│  ┌──────┐ ┌──────┐                                      │
│  │ MySQL │ │ ...  │                                      │
│  │ 启动  │ │      │                                      │
│  └──────┘ └──────┘                                      │
│  缓存                                                    │
│  ┌──────┐                                                │
│  │ Redis │                                                │
│  └──────┘                                                │
│  中间件 / 微服务                                          │
│  ┌──────┐ ┌──────┐ ┌──────┐                             │
│  │Rabbit│ │Nacos │ │Sent..│                             │
│  └──────┘ └──────┘ └──────┘                             │
│                                            全部启动       │
├─────────────────────────────────────────────────────────┤
│  MySQL 日志                                              │
│  [2026-06-18 20:30:01] [Note]  ready for connections     │
└─────────────────────────────────────────────────────────┘
```

> (截图待补充)

---

## 功能

| 功能 | 说明 |
|------|------|
| **服务启停控制** | 一键启动/停止任意本地服务，支持优雅停止与强制结束 |
| **批量启停** | 按分组「全部启动」/「全部停止」，快速拉起一组服务 |
| **服务分组展示** | 自动按组（数据库、缓存、微服务等）分类展示服务卡片 |
| **实时日志查看** | 服务的 stdout/stderr 实时输出到前端日志面板 |
| **端口自动检测** | 自动检测服务端口占用状态，运行中 / 已停止一目了然 |
| **外部运行服务检测** | 识别非本工具启动的已运行服务进程 |
| **搜索过滤** | 按名称快速筛选服务 |
| **服务 CRUD** | 在 UI 中直接新增、编辑、删除服务配置，无需修改 JSON |
| **Tauri 桌面应用** | 可打包为独立的 Windows 桌面应用 |
| **自定义颜色标识** | 每个服务/分组可自定义颜色，视觉上一目了然 |

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **前端** | **Vue 3** + **Element Plus** + **Vite** | 现代化 SPA，组合式 API |
| **后端** | **Python FastAPI** + **Uvicorn** | 异步 API，进程管理 |
| **桌面壳** | **Tauri v2** (Rust) | 可选，也可纯浏览器使用 |
| **通信** | RESTful JSON API | 前后端分离架构 |

---

## 快速开始

### 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **npm** 9+

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端默认运行在 **<http://localhost:8710>**

### 2. 启动前端（开发模式）

```bash
npm install
npm run dev
```

前端默认运行在 **<http://localhost:1420>**

### 3. 一键启动前后端

```bash
npm run dev:all
```

### 4. Tauri 桌面应用（可选）

```bash
npm run tauri dev
```

---

## 配置

### 服务配置

服务列表存储在 `backend/services.json`，格式如下：

```json
[
  {
    "id": "mysql",
    "name": "MySQL",
    "command": "D:\\tool\\mysql\\bin\\mysqld --defaults-file=D:\\tool\\mysql\\my.ini --console",
    "group": "数据库",
    "color": "#409eff",
    "url": null,
    "version": null
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一标识符 |
| `name` | string | 显示名称 |
| `command` | string | 启动命令（命令行或可执行路径） |
| `group` | string | 分组名，相同分组的服务卡片会放在一起 |
| `color` | string | 主题色，十六进制颜色值 |
| `url` | string? | 服务 Web 管理页面的链接 |
| `version` | string? | 版本号标识 |
| `cwd` | string? | 工作目录 |
| `port` | number? | 端口号，用于检测服务状态 |
| `env` | object? | 额外环境变量 |

> **提示**：你也可以直接在 Web UI 中新增、编辑、删除服务，无需手动编辑 JSON。

### 后端配置

后端配置在 `backend/main.py` 中，可调整以下参数：

- `--host`：监听地址，默认 `0.0.0.0`
- `--port`：监听端口，默认 `8710`

---

## 项目结构

```
OneStopService/
├── backend/                      # Python 后端
│   ├── main.py                  # FastAPI 入口 & 应用配置
│   ├── config.py                # services.json 的 CRUD 操作
│   ├── models.py                # Pydantic 数据模型
│   ├── process_manager.py       # 进程管理（启动/停止/检测/日志读取）
│   ├── log_store.py             # 日志环形缓冲区
│   ├── services.json            # 服务列表配置文件
│   ├── requirements.txt         # Python 依赖
│   └── routers/
│       ├── __init__.py
│       ├── health.py            # 健康检查端点
│       ├── services.py          # 服务配置 CRUD API
│       └── processes.py         # 进程启停/日志/状态 API
├── src/                         # Vue 3 前端
│   ├── App.vue                  # 主页面（布局、搜索、批量操作）
│   ├── main.js                  # 入口文件，注册 Element Plus 等
│   ├── constants.js             # 分组/颜色常量
│   ├── api/
│   │   └── index.js             # Axios API 封装
│   ├── assets/
│   ├── styles/
│   └── components/
│       ├── ServiceCard.vue      # 服务卡片（启停按钮、状态指示）
│       ├── ServiceForm.vue      # 新增/编辑服务对话框
│       ├── LogPanel.vue         # 日志面板（实时输出流）
│       └── StatusBar.vue        # 底部状态栏
├── src-tauri/                   # Tauri 桌面应用壳
│   ├── src/
│   │   └── main.rs              # Rust 入口
│   ├── Cargo.toml
│   ├── tauri.conf.json          # Tauri 配置（窗口大小、标题等）
│   └── icons/                   # 应用图标
├── public/                      # 静态资源
├── dist/                        # 构建输出
├── index.html                   # HTML 入口
├── vite.config.js               # Vite 配置
├── package.json                 # 前端依赖 & 脚本
└── README.md                    # 本文件
```

---

## API 概览

后端提供以下 RESTful API 端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/services` | 获取所有服务配置 |
| `POST` | `/api/services` | 新增服务 |
| `PUT` | `/api/services/{id}` | 更新服务 |
| `DELETE` | `/api/services/{id}` | 删除服务 |
| `GET` | `/api/processes` | 获取所有进程状态 |
| `POST` | `/api/processes/{id}/start` | 启动服务 |
| `POST` | `/api/processes/{id}/stop` | 停止服务 |
| `POST` | `/api/processes/start-batch` | 批量启动 |
| `POST` | `/api/processes/stop-batch` | 批量停止 |
| `GET` | `/api/processes/{id}/logs` | 获取日志 (SSE 流) |

---

## 开发指南

### 端口约定

| 用途 | 端口 |
|------|------|
| Vite 开发服务器 | `1420` |
| FastAPI 后端 | `8710` |

### 后端模块说明

- **`process_manager.py`**：核心模块。管理进程生命周期，支持 subprocess 启停、端口检测、外部进程识别、日志流读取。
- **`log_store.py`**：基于环形缓冲区的日志存储，支持 SSE 实时推送。
- **`config.py`**：JSON 文件 CRUD，带读写锁保证并发安全。

### 构建桌面应用

```bash
npm run tauri build
```

构建产物位于 `src-tauri/target/release/bundle/`。

---

## 预配置服务

本工具开箱即支持以下本地服务的管理配置：

| 服务 | 分组 | 管理地址 |
|------|------|----------|
| **MySQL** 8.x | 数据库 | — |
| **Redis** 3.x | 缓存 | — |
| **RabbitMQ** 4.x | 中间件 | <http://localhost:15672> |
| **Nacos** 2.x | 微服务 | <http://localhost:8849> |
| **Sentinel** 1.8.x | 微服务 | <http://localhost:8888> |
| **ZipKin** 3.x | 微服务 | <http://localhost:9411> |

可根据需要在 UI 中自由增删改。

---

## 许可证

本项目仅供个人学习与开发环境使用。

---

*Made for local development productivity.*
