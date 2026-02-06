// Sora 视频抓包后台脚本
console.log('Sora 视频抓包助手已启动');

// 存储配置
let config = {
  apiUrl: 'http://localhost:8000',
  autoSend: true,
  enabled: true
};

// 从存储加载配置
chrome.storage.sync.get(['apiUrl', 'autoSend', 'enabled'], (result) => {
  if (result.apiUrl) config.apiUrl = result.apiUrl;
  if (result.autoSend !== undefined) config.autoSend = result.autoSend;
  if (result.enabled !== undefined) config.enabled = result.enabled;
  console.log('配置已加载:', config);
});

// 监听配置变化
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync') {
    if (changes.apiUrl) config.apiUrl = changes.apiUrl.newValue;
    if (changes.autoSend) config.autoSend = changes.autoSend.newValue;
    if (changes.enabled) config.enabled = changes.enabled.newValue;
    console.log('配置已更新:', config);
  }
});

// 监听来自 content script 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('收到消息:', request.type);
  
  if (request.type === 'VIDEO_DATA') {
    handleVideoData(request.data, sendResponse);
    return true; // 保持消息通道开启
  }
  
  if (request.type === 'GET_CONFIG') {
    sendResponse({ config });
    return true;
  }
  
  if (request.type === 'UPDATE_CONFIG') {
    config = { ...config, ...request.config };
    chrome.storage.sync.set(config);
    sendResponse({ success: true });
    return true;
  }
  
  // 新增：通用的后端请求代理（绕过 CORS）
  if (request.type === 'SEND_TO_BACKEND') {
    handleBackendRequest(request, sendResponse);
    return true; // 保持消息通道开启
  }
});

// 处理视频数据
async function handleVideoData(data, sendResponse) {
  if (!config.enabled) {
    console.log('插件已禁用，跳过处理');
    sendResponse({ success: false, message: '插件已禁用' });
    return;
  }

  try {
    console.log('处理数据，类型:', data.type || 'VIDEO_DATA');
    
    // 根据数据类型选择不同的处理方式
    if (data.type) {
      // 新的多类型数据
      await handleMultiTypeData(data, sendResponse);
    } else {
      // 原有的视频数据
      await handleLegacyVideoData(data, sendResponse);
    }
  } catch (error) {
    console.error('处理数据失败:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// 处理通用的后端请求（绕过 CORS）
async function handleBackendRequest(request, sendResponse) {
  try {
    const { endpoint, method = 'GET', data } = request;
    const url = `${config.apiUrl}${endpoint}`;
    
    console.log(`📡 代理请求: ${method} ${url}`);
    
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('✅ 代理请求成功');
    
    sendResponse({ success: true, result });
  } catch (error) {
    console.error('❌ 代理请求失败:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// 处理多类型数据
async function handleMultiTypeData(data, sendResponse) {
  console.log('处理多类型数据:', data.type);
  
  try {
    const result = await sendToBackend(data, '/api/data/capture');
    sendResponse({ success: true, result });
  } catch (error) {
    console.error('发送失败:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// 处理传统视频数据
async function handleLegacyVideoData(data, sendResponse) {
  console.log('处理视频数据');
  
  // 提取关键信息
  const videoInfo = extractVideoInfo(data);
  console.log('提取的视频信息:', videoInfo);
  
  // 如果启用自动发送，则发送到后端
  if (config.autoSend) {
    const result = await sendToBackend(videoInfo, '/api/videos/capture');
    sendResponse({ success: true, result });
  } else {
    // 保存到本地存储
    await saveToLocal(videoInfo);
    sendResponse({ success: true, message: '已保存到本地' });
  }
}

// 提取视频信息
function extractVideoInfo(data) {
  const post = data.post || {};
  const profile = data.profile || {};
  const attachment = post.attachments?.[0] || {};
  
  return {
    // 帖子基本信息
    post_id: post.id,
    text: post.text,
    caption: post.caption,
    posted_at: post.posted_at,
    updated_at: post.updated_at,
    permalink: post.permalink,
    share_ref: post.share_ref,
    
    // 统计信息
    like_count: post.like_count,
    view_count: post.view_count,
    unique_view_count: post.unique_view_count,
    remix_count: post.remix_count,
    reply_count: post.reply_count,
    
    // 用户信息
    user_id: profile.user_id,
    username: profile.username,
    profile_picture_url: profile.profile_picture_url,
    verified: profile.verified,
    
    // 视频信息
    generation_id: attachment.generation_id,
    task_id: attachment.task_id,
    video_url: attachment.url,
    downloadable_url: attachment.downloadable_url,
    download_url_watermark: attachment.download_urls?.watermark,
    download_url_no_watermark: attachment.download_urls?.no_watermark,
    
    // 视频属性
    width: attachment.width,
    height: attachment.height,
    n_frames: attachment.n_frames,
    prompt: attachment.prompt || post.text,
    
    // 编码信息
    source_url: attachment.encodings?.source?.path,
    source_size: attachment.encodings?.source?.size,
    thumbnail_url: attachment.encodings?.thumbnail?.path,
    md_url: attachment.encodings?.md?.path,
    ld_url: attachment.encodings?.ld?.path,
    gif_url: attachment.encodings?.gif?.path,
    
    // 其他信息
    emoji: post.emoji,
    discovery_phrase: post.discovery_phrase,
    source: post.source,
    
    // 时间戳
    captured_at: new Date().toISOString()
  };
}

// 发送到后端
async function sendToBackend(data, endpoint = '/api/videos/capture') {
  try {
    const url = `${config.apiUrl}${endpoint}`;
    console.log('发送到后端:', url);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('发送成功:', result);
    
    // 显示通知
    try {
      const message = getNotificationMessage(data);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Sora 数据抓包成功',
        message: message
      });
    } catch (e) {
      console.log('通知显示失败:', e);
    }
    
    return result;
  } catch (error) {
    console.error('发送到后端失败:', error);
    
    // 显示错误通知
    try {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Sora 数据抓包失败',
        message: error.message
      });
    } catch (e) {
      console.log('错误通知显示失败:', e);
    }
    
    throw error;
  }
}

// 获取通知消息
function getNotificationMessage(data) {
  if (data.type === 'USER_INFO') {
    return `用户信息: ${data.data?.username || data.data?.email}`;
  } else if (data.type === 'QUOTA') {
    const remaining = data.data?.estimated_num_videos_remaining || data.data?.remaining || 0;
    const credit = data.data?.credit_remaining || 0;
    return `配额: 剩余 ${remaining} 个视频, ${credit} 积分`;
  } else if (data.type === 'CREATE_VIDEO') {
    return `创建视频: ${data.data?.prompt?.substring(0, 30)}...`;
  } else if (data.type === 'VIDEO_PROGRESS') {
    const progress = (data.data?.progress_pct || 0) * 100;
    return `视频进度: ${progress.toFixed(1)}% - ${data.data?.status}`;
  } else {
    // 视频详情
    return `已捕获视频: ${data.text || data.prompt || data.discovery_phrase || '未知标题'}`;
  }
}

// 保存到本地存储
async function saveToLocal(videoInfo) {
  return new Promise((resolve, reject) => {
    chrome.storage.local.get(['capturedVideos'], (result) => {
      const videos = result.capturedVideos || [];
      videos.push(videoInfo);
      
      // 只保留最近 100 条
      if (videos.length > 100) {
        videos.shift();
      }
      
      chrome.storage.local.set({ capturedVideos: videos }, () => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          console.log('已保存到本地存储');
          resolve();
        }
      });
    });
  });
}
