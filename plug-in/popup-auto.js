// Popup 脚本 - 显示发布队列状态
console.log('🎨 Popup 脚本已加载');

// DOM 元素
const statusDiv = document.getElementById('status');
const queueLengthSpan = document.getElementById('queueLength');
const currentTabSpan = document.getElementById('currentTab');
const refreshBtn = document.getElementById('refreshBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const logDiv = document.getElementById('log');

// 日志记录
function addLog(message) {
  const logItem = document.createElement('div');
  logItem.className = 'log-item';
  logItem.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  logDiv.appendChild(logItem);
  
  // 自动滚动到底部
  logDiv.scrollTop = logDiv.scrollHeight;
  
  // 限制日志条数
  while (logDiv.children.length > 50) {
    logDiv.removeChild(logDiv.firstChild);
  }
}

// 更新状态显示
function updateStatus() {
  chrome.runtime.sendMessage({ type: 'GET_QUEUE_STATUS' }, (response) => {
    if (!response) return;
    
    const { queueLength, isProcessing, currentTab } = response;
    
    // 更新队列长度
    queueLengthSpan.textContent = queueLength;
    
    // 更新当前标签页
    currentTabSpan.textContent = currentTab ? `Tab ${currentTab}` : '无';
    
    // 更新状态
    if (isProcessing) {
      statusDiv.className = 'status processing';
      statusDiv.textContent = '🚀 正在发布...';
      startBtn.disabled = true;
      stopBtn.disabled = false;
    } else if (queueLength > 0) {
      statusDiv.className = 'status idle';
      statusDiv.textContent = '⏸️ 队列中有待发布的草稿';
      startBtn.disabled = false;
      stopBtn.disabled = true;
    } else {
      statusDiv.className = 'status idle';
      statusDiv.textContent = '✅ 队列为空';
      startBtn.disabled = true;
      stopBtn.disabled = true;
    }
  });
}

// 刷新队列
refreshBtn.addEventListener('click', () => {
  addLog('手动刷新队列...');
  refreshBtn.disabled = true;
  refreshBtn.textContent = '刷新中...';
  
  chrome.runtime.sendMessage({ type: 'FETCH_QUEUE' }, (response) => {
    refreshBtn.disabled = false;
    refreshBtn.textContent = '刷新队列';
    
    if (response && response.success) {
      addLog(`✅ 刷新成功，队列长度: ${response.queueLength}`);
      updateStatus();
    } else {
      addLog(`❌ 刷新失败: ${response?.error || '未知错误'}`);
    }
  });
});

// 开始发布
startBtn.addEventListener('click', () => {
  addLog('开始发布队列...');
  chrome.runtime.sendMessage({ type: 'START_PUBLISH' }, (response) => {
    if (response.success) {
      addLog('✅ 发布已启动');
      updateStatus();
    } else {
      addLog(`❌ 启动失败: ${response.message}`);
    }
  });
});

// 停止发布
stopBtn.addEventListener('click', () => {
  addLog('停止发布...');
  chrome.runtime.sendMessage({ type: 'STOP_PUBLISH' }, (response) => {
    if (response.success) {
      addLog('✅ 已停止发布');
      updateStatus();
    }
  });
});

// 初始化
addLog('Popup 已加载');
updateStatus();

// 定时更新状态（每秒）
setInterval(updateStatus, 1000);

// 监听来自 background 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'LOG') {
    addLog(message.message);
  }
});
