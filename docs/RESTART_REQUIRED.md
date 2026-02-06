# ⚠️ 需要重启服务

## 修改内容

已修改 `backend/python自动化/sora_automation.py` 中的 `_wait_for_video` 方法：

1. **移除超时检测**：改为无限等待
2. **优化成功检测**：优先检查 `video_url`
3. **支持 published 状态**：检测 `status in ['success', 'published']`

## 重启步骤

### 1. 停止当前运行的服务

如果有正在运行的任务，请等待完成或手动停止。

### 2. 清除 Python 缓存

```bash
# Windows PowerShell
Get-ChildItem -Path "backend" -Filter "*.pyc" -Recurse | Remove-Item -Force
Get-ChildItem -Path "backend" -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force

# Linux/Mac
find backend -name "*.pyc" -delete
find backend -name "__pycache__" -type d -exec rm -rf {} +
```

### 3. 重启后端服务

```bash
# 停止旧进程
# Ctrl+C 或 kill 进程

# 启动新进程
python backend/app.py
```

### 4. 验证修改

启动后，查看日志应该显示：

```
等待视频生成完成...
⚠️  已禁用超时检测，将一直等待直到成功或失败
```

当任务状态更新为 `published` 时，应该立即检测到：

```
✓ 检测到任务状态已更新为 published（插件已完成匹配）
✓ 视频生成完成！
```

## 注意事项

1. **必须重启**：Python 会缓存已导入的模块，修改代码后必须重启才能生效
2. **清除缓存**：`.pyc` 文件和 `__pycache__` 目录包含编译后的字节码，需要清除
3. **等待任务完成**：如果有正在运行的任务，建议等待完成后再重启

## 验证清单

- [ ] 已停止后端服务
- [ ] 已清除 Python 缓存文件
- [ ] 已重启后端服务
- [ ] 日志显示"已禁用超时检测"
- [ ] 新任务能正确检测 `published` 状态
- [ ] 不再出现"超时 (600秒)"错误
