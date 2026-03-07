# 更新日志

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-07

### Added
- MiniMax API 集成，使用 MiniMax 大语言模型进行对话生成
- 私聊支持：支持自动与私聊用户进行主动对话
- 群聊支持：支持在群聊中自动发起对话
- 定时触发：根据配置的时间间隔自动触发对话
- 沉默检测：群聊沉默指定时间后自动触发对话
- 自动触发：插件启动后指定时间自动发起对话
- 免打扰时段：支持设置免打扰时段，避免在特定时间打扰用户
- TTS 语音合成：支持将回复转换为语音发送
- 文转图功能：支持将长消息转换为图片发送
- 读空气功能：使用 LLM 判断群聊是否需要回复
- 提醒功能：支持设置定时提醒
- LLM 拦截功能：可使用配置的 LLM 替换默认对话

### Dependencies
- 初始版本发布
