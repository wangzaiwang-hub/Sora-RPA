# Progress Message 自动更新机制

## 问题描述

之前的实现中，当任务状态更新时，`progress_message` 字段没有同步更新，导致：
- 任务状态是 `success`，但 `progress_message` 还是"视频生成中 (531秒)"
- 任务状态是 `failed`，但 `progress_message` 还是"视频生成中"

这会导致 API 返回的数据不一致，前端显示错误的进度信息。

## 解决方案

### 1. 修改 `update_task_status` 方法

在 `backend/database.py` 的 `update_task_status` 方法中添加自动更新逻辑：

```python
# 根据状态自动设置 progress 和 progress_message
if status == 'success' or status == 'published':
    progress = 100
    progress_message = 'completed'
elif status == 'failed':
    progress = 0
    progress_message = f'失败: {error_message}'
elif status == 'running':
    # running 状态不修改 progress_message，保留之前的进度信息
    pass
```

### 2. 更新规则

| 任务状态 | progress | progress_message | 说明 |
|---------|----------|------------------|------|
| `success` | 100 | `completed` | 任务成功完成 |
| `published` | 100 | `completed` | 任务已发布（也算完成） |
| `failed` | 0 | `失败: {error_message}` | 任务失败 |
| `running` | 保持不变 | 保持不变 | 运行中，保留进度信息 |
| `pending` | 0 | `null` | 待处理 |

### 3. 影响范围

所有调用 `update_task_status` 的地方都会自动应用这个规则：

- `backend/window_manager.py` - 任务执行完成时
- `backend/app.py` - 各种 API 端点更新任务状态时
- 其他脚本调用 `db.update_task_status()` 时

## 修复历史数据

对于已经存在的错误数据，可以运行修复脚本：

```bash
# 修复状态为 success/published 但 progress_message 不正确的任务
python backend/fix_progress_message.py

# 修复状态为 failed 但有 video_url 的任务
python backend/fix_failed_with_url.py
```

## API 返回示例

### 修复前
```json
{
  "id": "video_64",
  "status": "completed",
  "progress": 100,
  "progress_message": "视频生成中 (531秒)",  // ❌ 错误
  "video_url": "https://..."
}
```

### 修复后
```json
{
  "id": "video_64",
  "status": "completed",
  "progress": 100,
  "progress_message": "completed",  // ✅ 正确
  "video_url": "https://..."
}
```

## 测试

创建一个新任务并观察状态变化：

```python
# 任务开始
db.update_task_status(task_id, 'running', start_time=now)
# progress_message 保持不变（如"视频生成中"）

# 任务成功
db.update_task_status(task_id, 'success', end_time=now)
# progress = 100, progress_message = 'completed'

# 任务失败
db.update_task_status(task_id, 'failed', error_message='超时')
# progress = 0, progress_message = '失败: 超时'
```

## 注意事项

1. **向后兼容**：修改不会影响现有代码的调用方式
2. **自动化**：不需要手动指定 `progress` 和 `progress_message`
3. **一致性**：确保所有任务的状态和进度信息保持一致
4. **运行中任务**：`running` 状态不会覆盖进度信息，保留详细的生成进度

## 相关文件

- `backend/database.py` - 核心修改
- `backend/fix_progress_message.py` - 修复历史数据
- `backend/window_manager.py` - 调用 `update_task_status`
- `backend/app.py` - 多处调用 `update_task_status`
