# 更新日志

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-03-07

### Added
- 新增表情包转述功能：自动将历史上下文中的表情包/图片消息发送给多模态大模型转述
- 支持选择使用 AstrBot 内置 LLM Provider 或 MiniMax API 进行图片描述
- 新增配置开关，可自选开启或关闭表情包转述功能
- 使用 _special 字段支持用户通过下拉菜单选择 LLM 提供商

### Fixed
- 使用 ruff 修复未使用的导入问题
- 修复配置文件：移除不支持的 category 类型（AstrBot 不支持此类型）
- 修复 provider 选择逻辑，支持用户选择的特定 provider

## [1.1.0] - 2026-03-07

### Changed
- 移除分段发送功能
- 移除历史记录保存功能
- 重构代码文件结构，将核心代码移至 src 目录
- 使用 ruff 进行代码检查和格式化

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

### Dependencies
- 初始版本发布
