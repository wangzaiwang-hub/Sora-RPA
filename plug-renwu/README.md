# Plug-renwu - Sora 视频数据抓包插件

## 📋 功能说明

plug-renwu 是一个 Chrome 浏览器插件，用于抓取 Sora 视频相关的数据。

### 核心功能

1. **用户信息抓取**
   - 账号邮箱、用户名
   - 邀请码和剩余邀请次数
   - 个人资料信息

2. **配额信息抓取**
   - 剩余视频生成次数
   - 剩余积分
   - 速率限制状态

3. **视频创建抓取**
   - 任务 ID
   - 提示词
   - 创建时间

4. **视频进度抓取**
   - 生成进度百分比
   - 任务状态
   - 失败原因（如果有）

5. **草稿列表抓取**
   - 草稿 ID
   - 任务 ID
   - 提示词
   - 视频 URL
   - 违规信息（如果有）

6. **已发布视频抓取**
   - 视频 ID
   - 发布链接
   - 提示词
   - 观看数、点赞数等统计信息

## 🚀 使用方法

1. 安装插件
2. 访问 Sora 网站 (https://sora.chatgpt.com)
3. 插件会自动拦截 API 请求并抓取数据
4. 数据会自动发送到后端 (http://localhost:8000)

## 📊 抓取的 API 端点

- `/backend/project_y/v2/me` - 用户信息
- `/backend/nf/check` - 配额信息
- `/backend/nf/create` - 创建视频
- `/backend/nf/pending/v2` - 视频进度
- `/backend/project_y/profile/drafts` - 草稿列表
- `/backend/project_y/post/{video_id}` - 视频详情

## 🔧 配置

在 popup 界面可以配置：
- 后端 API 地址
- 是否自动发送数据
- 是否启用插件

## 📝 数据格式

所有抓取的数据都会通过 background.js 发送到后端的 `/api/data/capture` 接口。

数据格式：
```json
{
  "type": "USER_INFO" | "QUOTA" | "CREATE_VIDEO" | "VIDEO_PROGRESS" | "DRAFT" | "VIDEO_DETAIL",
  "data": { ... }
}
```

## ⚠️ 注意事项

- 插件只抓取数据，不修改任何请求
- 所有数据仅用于统计和分析
- 请确保后端服务正在运行
