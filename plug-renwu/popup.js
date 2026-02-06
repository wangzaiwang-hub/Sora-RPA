// Popup 脚本
document.addEventListener('DOMContentLoaded', async () => {
  // 加载配置
  await loadConfig();
  
  // 加载统计信息
  await loadStats();
  
  // 绑定事件
  bindEvents();
});

// 加载配置
async function loadConfig() {
  chrome.storage.sync.get(['apiUrl', 'autoSend', 'enabled'], (result) => {
    document.getElementById('apiUrl').value = result.apiUrl || 'http://localhost:8000';
    document.getElementById('autoSend').checked = result.autoSend !== false;
    document.getElementById('enabled').checked = result.enabled !== false;
    
    updateStatus(result.enabled !== false);
  });
}

// 加载统计信息
async function loadStats() {
  chrome.storage.local.get(['capturedVideos'], (result) => {
    const count = result.capturedVideos ? result.capturedVideos.length : 0;
    document.getElementById('count').textContent = count;
  });
}

// 更新状态显示
function updateStatus(enabled) {
  const statusEl = document.getElementById('status');
  if (enabled) {
    statusEl.textContent = '运行中';
    statusEl.style.color = '#10b981';
  } else {
    statusEl.textContent = '已停止';
    statusEl.style.color = '#ef4444';
  }
}

// 绑定事件
function bindEvents() {
  // 保存设置
  document.getElementById('saveBtn').addEventListener('click', async () => {
    const config = {
      apiUrl: document.getElementById('apiUrl').value,
      autoSend: document.getElementById('autoSend').checked,
      enabled: document.getElementById('enabled').checked
    };
    
    chrome.storage.sync.set(config, () => {
      showMessage('设置已保存', 'success');
      updateStatus(config.enabled);
      
      // 通知后台脚本
      chrome.runtime.sendMessage({ type: 'UPDATE_CONFIG', config });
    });
  });
  
  // 查看已捕获
  document.getElementById('viewBtn').addEventListener('click', () => {
    chrome.storage.local.get(['capturedVideos'], (result) => {
      const videos = result.capturedVideos || [];
      if (videos.length === 0) {
        showMessage('暂无捕获的视频', 'info');
      } else {
        // 在新标签页中显示
        const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(
          generateVideoListHtml(videos)
        );
        chrome.tabs.create({ url: dataUrl });
      }
    });
  });
  
  // 清除数据
  document.getElementById('clearBtn').addEventListener('click', () => {
    if (confirm('确定要清除所有已捕获的视频数据吗？')) {
      chrome.storage.local.set({ capturedVideos: [] }, () => {
        showMessage('数据已清除', 'success');
        loadStats();
      });
    }
  });
  
  // 导出数据
  document.getElementById('exportBtn').addEventListener('click', () => {
    chrome.storage.local.get(['capturedVideos'], (result) => {
      const videos = result.capturedVideos || [];
      if (videos.length === 0) {
        showMessage('暂无数据可导出', 'info');
        return;
      }
      
      const dataStr = JSON.stringify(videos, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `sora_videos_${Date.now()}.json`;
      a.click();
      
      URL.revokeObjectURL(url);
      showMessage('数据已导出', 'success');
    });
  });
  
  // 启用/禁用切换
  document.getElementById('enabled').addEventListener('change', (e) => {
    updateStatus(e.target.checked);
  });
}

// 显示消息
function showMessage(message, type = 'info') {
  const colors = {
    success: '#10b981',
    error: '#ef4444',
    info: '#3b82f6'
  };
  
  const messageEl = document.createElement('div');
  messageEl.textContent = message;
  messageEl.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 10px 20px;
    background: ${colors[type]};
    color: white;
    border-radius: 4px;
    z-index: 1000;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(messageEl);
  
  setTimeout(() => {
    messageEl.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => messageEl.remove(), 300);
  }, 2000);
}

// 生成视频列表 HTML
function generateVideoListHtml(videos) {
  const items = videos.map((video, index) => `
    <div class="video-item">
      <div class="video-header">
        <h3>#${index + 1} ${video.text || video.prompt || '无标题'}</h3>
        <span class="time">${new Date(video.captured_at).toLocaleString()}</span>
      </div>
      <div class="video-info">
        <p><strong>用户:</strong> ${video.username} (${video.user_id})</p>
        <p><strong>视频ID:</strong> ${video.post_id}</p>
        <p><strong>尺寸:</strong> ${video.width}x${video.height}</p>
        <p><strong>帧数:</strong> ${video.n_frames}</p>
        <p><strong>观看:</strong> ${video.view_count} | <strong>点赞:</strong> ${video.like_count}</p>
      </div>
      <div class="video-links">
        <a href="${video.downloadable_url}" target="_blank">下载视频</a>
        <a href="${video.permalink}" target="_blank">查看原帖</a>
        ${video.thumbnail_url ? `<a href="${video.thumbnail_url}" target="_blank">缩略图</a>` : ''}
      </div>
    </div>
  `).join('');
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>已捕获的 Sora 视频</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
          background: #f5f5f5;
        }
        h1 {
          color: #333;
          border-bottom: 2px solid #667eea;
          padding-bottom: 10px;
        }
        .video-item {
          background: white;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .video-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
        }
        .video-header h3 {
          margin: 0;
          color: #667eea;
        }
        .time {
          color: #666;
          font-size: 14px;
        }
        .video-info {
          margin-bottom: 15px;
          line-height: 1.6;
        }
        .video-info p {
          margin: 5px 0;
        }
        .video-links {
          display: flex;
          gap: 10px;
        }
        .video-links a {
          padding: 8px 16px;
          background: #667eea;
          color: white;
          text-decoration: none;
          border-radius: 4px;
          font-size: 14px;
        }
        .video-links a:hover {
          background: #5568d3;
        }
      </style>
    </head>
    <body>
      <h1>已捕获的 Sora 视频 (${videos.length})</h1>
      ${items}
    </body>
    </html>
  `;
}
