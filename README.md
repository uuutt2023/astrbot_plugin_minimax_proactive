# MiniMax 主动对话插件

<p align="center">
  <img src="https://img.shields.io/badge/ AstrBot Plugin-blue" alt="AstrBot Plugin">
  <img src="https://img.shields.io/badge/Author-uuutt2023-orange" alt="Author">
</p>

## 简介

MiniMax 主动对话插件是一个基于 MiniMax API 的 AstrBot 插件，能够自动与用户进行主动对话。该插件支持私聊和群聊场景，可以根据配置的时间间隔自动触发对话。

## 功能特性

### 核心功能

- **MiniMax API 集成**: 使用 MiniMax 大语言模型进行对话生成
- **私聊支持**: 支持自动与私聊用户进行主动对话
- **群聊支持**: 支持在群聊中自动发起对话
- **定时触发**: 根据配置的时间间隔自动触发对话
- **沉默检测**: 群聊沉默指定时间后自动触发对话
- **自动触发**: 插件启动后指定时间自动发起对话
- **免打扰时段**: 支持设置免打扰时段，避免在特定时间打扰用户
- **TTS 语音合成**: 支持将回复转换为语音发送
- **文转图功能**: 支持将回复转换为图片发送
- **读空气功能**: 使用LLM判断是否需要回复
- **提醒功能**: 支持设置定时提醒

### 配置选项

- **API 配置**: MiniMax API Key、模型选择、温度参数等
- **调度设置**: 最小/最大间隔时间、每日触发上限、免打扰时段
- **触发设置**: 沉默触发分钟数、自动触发延迟
- **TTS 设置**: 启用/禁用语音、语音后是否同时发送文本
- **分段设置**: 启用/禁用分段、分段阈值、发送间隔

## 模块结构

```
astrbot_plugin_minimax_proactive/
├── main.py                   # 插件入口
├── metadata.yaml             # 插件元数据
├── _conf_schema.json        # 配置架构
│
├── business/                 # 业务模块
│   ├── __init__.py
│   ├── config_manager.py    # 配置管理器
│   └── constants.py         # 业务常量
│
├── core/                     # 核心业务逻辑
│   ├── __init__.py
│   └── proactive_core.py    # 主动对话核心
│
├── services/                 # 服务层（DI容器）
│   └── __init__.py         # 协议定义、DI容器
│
├── handlers/                 # 消息处理器
│   ├── __init__.py
│   ├── message_processor.py # 消息处理器
│   ├── message_cleaner.py  # 消息清理
│   ├── reminder.py         # 提醒功能
│   └── messager.py         # 消息发送器
│
├── llm/                      # LLM 层
│   ├── __init__.py
│   ├── caller.py            # LLM 调用器
│   └── image_caption.py     # 图片转述工具
│
├── storage/                  # 存储层
│   ├── __init__.py
│   ├── storage.py
│   └── scheduler.py
│
├── utils/                    # 通用工具
│   ├── __init__.py
│   ├── event_utils.py
│   ├── text_utils.py
│   ├── time_utils.py
│   ├── helpers.py
│   └── decorators.py        # 装饰器（注解模式）
│
└── prompts/                  # 提示词模板
    ├── __init__.py
    ├── group_proactive.txt   # 群聊主动对话
    ├── private_proactive.txt # 私聊主动对话
    ├── image_desc.txt        # 图片描述
    ├── read_air.txt         # 读空气判断
    └── help.txt             # 帮助信息
```

## 设计模式

### 依赖注入模式

使用 `DIContainer` 或 `ServiceContainer` 实现依赖注入：

```python
from services import DIContainer, ServiceContainer

# 方式1: 使用 ServiceContainer（推荐）
container = ServiceContainer()
storage = container.storage
llm = container.llm

# 方式2: 自定义 DIContainer
container = DIContainer()
container.register_singleton(StorageProtocol, lambda data_dir: Storage(data_dir))
container.register(LLMProtocol, lambda ctx, cfg: LLMCaller(ctx, cfg))
storage = container.resolve(StorageProtocol)
```

### 注解模式

使用装饰器简化常见操作：

```python
from utils.decorators import log, error_handler, timed, async_retry

@log("执行主动对话")
@error_handler(default_return="出错了")
@timed()
@async_retry(max_attempts=3)
async def proactive_chat(session_id: str, message: str):
    # ...
    pass
```

## 安装配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 AstrBot

在 AstrBot 配置文件中添加以下配置：

```yaml
minimax_proactive:
  # MiniMax API 配置
  api_key: "your-api-key"
  base_url: "https://api.minimax.chat"
  model: "abab6.5s-chat"
  
  # 私聊会话配置
  private_sessions:
    - enable: true
      session_id: "123456789"
      session_name: "用户1"
      proactive_prompt: "你现在是一个友好的助手..."
      schedule_settings:
        min_interval_minutes: 30
        max_interval_minutes: 900
        max_unanswered_times: 3
        quiet_hours: "1-7"
  
  # 群聊会话配置
  group_sessions:
    - enable: true
      session_id: "987654321"
      session_name: "测试群"
      proactive_prompt: "你在一个群里活跃气氛..."
      schedule_settings:
        min_interval_minutes: 30
        max_interval_minutes: 900
        max_unanswered_times: 3
        quiet_hours: "1-7"
      group_idle_trigger_minutes: 10
      auto_trigger_settings:
        enable_auto_trigger: true
        auto_trigger_after_minutes: 5
```

## 使用方法

### 消息触发

当用户在配置的私聊/群聊中发送消息时，插件会记录时间并重置对话计数器。下次触发时间将根据配置的时间间隔随机计算。

### 沉默触发

当群聊中超过指定时间（`group_idle_trigger_minutes`）没有新消息时，插件会自动触发对话。

### 自动触发

插件启动后，如果启用自动触发（`enable_auto_trigger`），会在指定时间（`auto_trigger_after_minutes`）后自动发起对话。

### 指令系统

| 指令 | 说明 |
|------|------|
| `/mpro help` | 显示帮助信息 |
| `/mpro status` | 显示功能状态 |
| `/mpro add <时间> <内容>` | 添加提醒 |
| `/mpro ls` | 列出提醒 |
| `/mpro rm <序号>` | 删除提醒 |
| `/mpro clear` | 清除所有提醒 |

## 配置说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `api_key` | string | MiniMax API 密钥 |
| `base_url` | string | API 地址 |
| `model` | string | 使用的模型 |
| `session_id` | string | 私聊用户ID或群聊ID |
| `enable` | bool | 是否启用 |
| `session_name` | string | 会话名称（用于显示） |
| `proactive_prompt` | string | 主动对话提示词 |
| `min_interval_minutes` | int | 最小触发间隔（分钟） |
| `max_interval_minutes` | int | 最大触发间隔（分钟） |
| `max_unanswered_times` | int | 最大连续未回复次数 |
| `quiet_hours` | string | 免打扰时段，格式"时-时" |
| `group_idle_trigger_minutes` | int | 群聊沉默触发时间 |
| `enable_auto_trigger` | bool | 是否启用自动触发 |
| `auto_trigger_after_minutes` | int | 启动后自动触发延迟 |

## 注意事项

1. 请确保 MiniMax API Key 正确配置
2. 建议设置合理的触发间隔，避免过度打扰用户
3. 免打扰时段的格式为"开始小时-结束小时"，例如"1-7"表示凌晨1点到早上7点
4. 首次使用建议先测试 API 连接是否正常
5. 提示词模板位于 `prompts/` 目录，可根据需要自定义

## 更新日志

### v1.0.0

- 初始版本
- 支持 MiniMax API 对话
- 支持私聊/群聊主动对话
- 支持定时触发、沉默触发、自动触发
- 支持 TTS 语音合成
- 支持消息分段发送

## 许可证

本项目采用 GNU Affero General Public License v3.0 (AGPLv3) 开源许可证。

详细许可证内容请参见 [LICENSE](LICENSE) 文件。
