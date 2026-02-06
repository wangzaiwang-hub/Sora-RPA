// Plug-in Background Script - 自动发布管理器
console.log('🚀 Plug-in 自动发布管理器已启动');
console.log('📅 启动时间:', new Date().toLocaleString());

// 发布队列
let publishQueue = [];
let isProcessing = false;
let currentTabId = null;

// 后端 API 地址
const BACKEND_URL = 'http://localhost:8000';

// 🆕 保持 Service Worker 活跃 - 多重策略
// Chrome 的 Service Worker 会在 30 秒无活动后休眠
// 使用多种方法来保持活跃

let keepAliveInterval = null;
let alarmInterval = null;
let portConnection = null;

// 策略1: 定时器心跳（每15秒）
function startKeepAlive() {
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval);
  }
  
  keepAliveInterval = setInterval(() => {
    console.log('💓 心跳:', new Date().toLocaleTimeString());
    
    // 发送消息给自己
    chrome.runtime.sendMessage({ type: 'KEEP_ALIVE' }).catch(() => {});
    
    // 查询标签页（触发活动）
    chrome.tabs.query({}, () => {});
    
    // 获取存储（触发活动）
    chrome.storage.local.get(['keepAlive'], () => {});
    
  }, 15000); // 每 15 秒
  
  console.log('💓 策略1: 定时器心跳已启动（每 15 秒）');
}

// 策略2: Chrome Alarms API（更可靠）
function startAlarmKeepAlive() {
  // 创建一个周期性alarm
  chrome.alarms.create('keepAlive', {
    periodInMinutes: 0.25 // 每 15 秒
  });
  
  console.log('💓 策略2: Alarm 心跳已启动（每 15 秒）');
}

// 监听alarm
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepAlive') {
    console.log('⏰ Alarm 触发:', new Date().toLocaleTimeString());
    // 执行一些轻量级操作
    chrome.storage.local.set({ lastAlarm: Date.now() });
  }
});

// 策略3: 长连接端口（保持连接）
function startPortConnection() {
  // 创建一个长连接端口
  try {
    portConnection = chrome.runtime.connect({ name: 'keepAlive' });
    
    portConnection.onDisconnect.addListener(() => {
      console.log('🔌 端口断开，重新连接...');
      setTimeout(startPortConnection, 1000);
    });
    
    // 定期发送消息
    setInterval(() => {
      if (portConnection) {
        try {
          portConnection.postMessage({ type: 'ping' });
        } catch (e) {
          console.log('🔌 端口发送失败，重新连接...');
          startPortConnection();
        }
      }
    }, 20000);
    
    console.log('💓 策略3: 长连接端口已建立');
  } catch (e) {
    console.log('⚠️ 无法建立端口连接:', e.message);
  }
}

// 策略4: 监听网络请求（被动保持活跃）
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    // 只记录到 Sora 的请求
    if (details.url.includes('sora.chatgpt.com')) {
      // 不打印日志，避免过多输出
    }
  },
  { urls: ["https://sora.chatgpt.com/*"] }
);

console.log('💓 策略4: 网络请求监听已启动');

// 启动所有策略
startKeepAlive();
startAlarmKeepAlive();
startPortConnection();

// 监听端口连接（策略3的接收端）
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'keepAlive') {
    port.onMessage.addListener((msg) => {
      if (msg.type === 'ping') {
        port.postMessage({ type: 'pong' });
      }
    });
  }
});

// 发送日志到 popup
function sendLogToPopup(message) {
  chrome.runtime.sendMessage({ type: 'LOG', message: message }).catch(() => {
    // Popup 可能未打开，忽略错误
  });
}

// 从后端获取草稿队列
async function fetchQueueFromBackend() {
  try {
    console.log('📡 从后端获取草稿队列...');
    console.log(`📍 请求 URL: ${BACKEND_URL}/api/drafts/queue`);
    
    const response = await fetch(`${BACKEND_URL}/api/drafts/queue`);
    
    console.log(`📡 响应状态: ${response.status} ${response.statusText}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const result = await response.json();
    console.log('📦 响应数据:', result);
    
    if (result.success && result.drafts) {
      console.log(`✅ 获取到 ${result.drafts.length} 个草稿`);
      
      if (result.drafts.length > 0) {
        console.log('📝 草稿列表:');
        result.drafts.forEach((draft, index) => {
          console.log(`  [${index + 1}] ${draft.draft_id} - ${draft.prompt?.substring(0, 30)}...`);
        });
        addToQueue(result.drafts);
      } else {
        console.log('ℹ️ 队列为空');
      }
    } else {
      console.warn('⚠️ 响应格式不正确:', result);
    }
    
  } catch (error) {
    console.error(`❌ 无法从后端获取队列: ${error.message}`);
    console.error('错误详情:', error);
  }
}

// 启动时立即获取一次
console.log('🔄 启动时获取队列...');
fetchQueueFromBackend();

// 定期从后端获取队列（每 10 秒）
console.log('⏰ 设置定时器：每 10 秒轮询一次');
setInterval(fetchQueueFromBackend, 10000);

/**
 * 添加草稿到发布队列
 */
function addToQueue(drafts) {
  drafts.forEach(draft => {
    // 检查是否已在队列中
    if (!publishQueue.some(d => d.draft_id === draft.draft_id)) {
      publishQueue.push(draft);
      console.log(`➕ 添加到队列: ${draft.draft_id}`);
      sendLogToPopup(`➕ 添加到队列: ${draft.draft_id}`);
    }
  });
  
  console.log(`📋 当前队列长度: ${publishQueue.length}`);
  sendLogToPopup(`📋 当前队列长度: ${publishQueue.length}`);
  
  // 开始处理队列
  if (!isProcessing) {
    processQueue();
  }
}

/**
 * 处理发布队列
 */
async function processQueue() {
  if (isProcessing || publishQueue.length === 0) {
    return;
  }
  
  isProcessing = true;
  console.log(`\n${'='.repeat(80)}`);
  console.log(`🎬 开始处理发布队列，共 ${publishQueue.length} 个草稿`);
  console.log('='.repeat(80));
  sendLogToPopup(`🎬 开始处理发布队列，共 ${publishQueue.length} 个草稿`);
  
  while (publishQueue.length > 0) {
    const draft = publishQueue.shift();
    
    console.log(`\n🚀 发布草稿 [剩余 ${publishQueue.length}]:`);
    console.log(`  草稿 ID: ${draft.draft_id}`);
    console.log(`  任务 ID: ${draft.task_id}`);
    console.log(`  草稿 URL: ${draft.draft_url}`);
    console.log(`  提示词: ${draft.prompt?.substring(0, 50)}...`);
    sendLogToPopup(`🚀 发布草稿: ${draft.draft_id} [剩余 ${publishQueue.length}]`);
    
    try {
      // 打开新标签页并发布
      const result = await publishDraft(draft);
      
      if (result.success) {
        console.log(`✅ 发布成功！`);
        console.log(`  发布 URL: ${result.published_url}`);
        console.log(`  Post ID: ${result.post_id}`);
        sendLogToPopup(`✅ 发布成功: ${result.post_id}`);
        
        // 从后端队列移除
        try {
          await fetch(`${BACKEND_URL}/api/drafts/queue/${draft.draft_id}`, {
            method: 'DELETE'
          });
          console.log(`  ✅ 已从后端队列移除: ${draft.draft_id}`);
        } catch (error) {
          console.warn(`  ⚠️ 无法从后端队列移除: ${error.message}`);
        }
        
        // 通知后端
        await notifyBackend(draft, result);
      } else {
        console.error(`❌ 发布失败: ${result.error}`);
        sendLogToPopup(`❌ 发布失败: ${result.error}`);
      }
      
    } catch (error) {
      console.error(`❌ 发布出错:`, error);
      sendLogToPopup(`❌ 发布出错: ${error.message}`);
    }
    
    // 等待一段时间再处理下一个
    if (publishQueue.length > 0) {
      console.log(`\n⏱️ 等待 5 秒后处理下一个...`);
      sendLogToPopup(`⏱️ 等待 5 秒后处理下一个...`);
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
  
  isProcessing = false;
  console.log(`\n${'='.repeat(80)}`);
  console.log(`✅ 发布队列处理完成`);
  console.log('='.repeat(80));
  sendLogToPopup(`✅ 发布队列处理完成`);
  
  // 清空后端队列
  try {
    await fetch(`${BACKEND_URL}/api/drafts/queue/clear`, {
      method: 'POST'
    });
    console.log('✅ 后端队列已清空');
  } catch (error) {
    console.warn('⚠️ 无法清空后端队列:', error.message);
  }
}

/**
 * 发布单个草稿
 */
async function publishDraft(draft) {
  return new Promise((resolve) => {
    // ✅ 在前台打开标签页，让用户看到发布过程
    // 不再切换回原标签页，避免 Chrome 的后台限制
    chrome.tabs.create({ 
      url: draft.draft_url, 
      active: true  // 保持激活状态
    }, (tab) => {
      currentTabId = tab.id;
      
      console.log(`  📍 已打开标签页: ${tab.id}`);
      console.log(`  👁️ 标签页保持激活，用户可以看到发布过程`);
      
      // 监听标签页加载完成
      const loadListener = (tabId, changeInfo, updatedTab) => {
        if (tabId === currentTabId && changeInfo.status === 'complete') {
          console.log(`  ✅ 页面加载完成`);
          
          // 等待一下，确保页面完全渲染
          setTimeout(() => {
            // 注入发布脚本
            chrome.scripting.executeScript({
              target: { tabId: currentTabId },
              files: ['auto-publish.js']
            }, () => {
              console.log(`  📤 已注入发布脚本`);
              console.log(`  🎬 开始自动发布流程...`);
            });
          }, 2000);
        }
      };
      
      chrome.tabs.onUpdated.addListener(loadListener);
      
      // 监听来自 content script 的发布结果
      const messageListener = (message, sender) => {
        if (sender.tab?.id === currentTabId && message.type === 'PUBLISH_RESULT') {
          console.log(`  📨 收到发布结果`);
          
          // 移除监听器
          chrome.tabs.onUpdated.removeListener(loadListener);
          chrome.runtime.onMessage.removeListener(messageListener);
          
          // 发布完成后关闭标签页
          if (currentTabId) {
            // 等待 2 秒让用户看到结果
            setTimeout(() => {
              chrome.tabs.remove(currentTabId, () => {
                console.log(`  ✅ 发布完成，已关闭标签页: ${currentTabId}`);
              });
              currentTabId = null;
            }, 2000);
          }
          
          // 返回结果
          resolve({
            success: message.success,
            published_url: message.published_url,
            post_id: message.post_id,
            error: message.error
          });
        }
      };
      
      chrome.runtime.onMessage.addListener(messageListener);
      
      // 超时保护（60秒）
      setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(loadListener);
        chrome.runtime.onMessage.removeListener(messageListener);
        
        if (currentTabId) {
          chrome.tabs.remove(currentTabId, () => {
            console.log(`  ⏱️ 超时，已关闭标签页: ${currentTabId}`);
          });
          currentTabId = null;
        }
        
        resolve({
          success: false,
          error: '发布超时'
        });
      }, 60000);
    });
  });
}

/**
 * 通知后端发布结果
 */
async function notifyBackend(draft, result) {
  try {
    const response = await fetch('http://localhost:8000/api/publish/result', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        draft_id: draft.draft_id,
        generation_id: draft.generation_id,
        task_id: draft.task_id,
        draft_url: draft.draft_url,
        published_url: result.published_url,
        post_id: result.post_id,
        success: result.success,
        timestamp: new Date().toISOString()
      })
    });
    
    if (response.ok) {
      console.log(`  ✅ 后端已更新`);
    } else {
      console.warn(`  ⚠️ 后端更新失败: ${response.status}`);
    }
  } catch (error) {
    console.warn(`  ⚠️ 无法连接后端:`, error.message);
  }
}

// 监听来自 popup 的命令和心跳消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 心跳消息
  if (message.type === 'KEEP_ALIVE') {
    sendResponse({ alive: true });
    return true;
  }
  
  // 获取队列状态
  if (message.type === 'GET_QUEUE_STATUS') {
    sendResponse({
      queueLength: publishQueue.length,
      isProcessing: isProcessing,
      currentTab: currentTabId
    });
    return true;
  }
  
  // 开始发布
  if (message.type === 'START_PUBLISH') {
    if (!isProcessing && publishQueue.length > 0) {
      processQueue();
      sendResponse({ success: true });
    } else {
      sendResponse({ success: false, message: '队列为空或正在处理中' });
    }
    return true;
  }
  
  // 停止发布
  if (message.type === 'STOP_PUBLISH') {
    publishQueue = [];
    isProcessing = false;
    if (currentTabId) {
      chrome.tabs.remove(currentTabId);
      currentTabId = null;
    }
    sendResponse({ success: true });
    return true;
  }
  
  // 手动获取队列
  if (message.type === 'FETCH_QUEUE') {
    fetchQueueFromBackend().then(() => {
      sendResponse({ 
        success: true, 
        queueLength: publishQueue.length 
      });
    }).catch(error => {
      sendResponse({ 
        success: false, 
        error: error.message 
      });
    });
    return true; // 保持消息通道开启
  }
  
  return true;
});

console.log('✅ Plug-in 自动发布管理器就绪');
console.log('💡 提示: 如果 Service Worker 休眠，请点击扩展图标或访问 Sora 网站来激活');
