// 在 Sora 视频详情页的控制台中运行此脚本
// 用于查看所有网络请求并找到包含视频数据的请求

console.log('%c🔍 开始检查网络请求', 'color: #667eea; font-size: 16px; font-weight: bold;');

// 获取当前视频 ID
const videoId = window.location.pathname.match(/\/p\/(s_[a-f0-9]+)/)?.[1];
console.log('🎯 当前视频 ID:', videoId);

// 存储所有请求
window.allRequests = [];
window.matchedRequests = [];

// 拦截 Fetch
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  const url = typeof args[0] === 'string' ? args[0] : args[0].url;
  const startTime = Date.now();
  
  const response = await originalFetch.apply(this, args);
  const clonedResponse = response.clone();
  
  try {
    const data = await clonedResponse.json();
    const duration = Date.now() - startTime;
    
    const requestInfo = {
      type: 'fetch',
      url: url,
      status: response.status,
      duration: duration,
      hasData: true,
      dataKeys: Object.keys(data),
      data: data
    };
    
    window.allRequests.push(requestInfo);
    
    // 检查是否包含视频 ID
    const urlContainsId = url.includes(videoId);
    const dataContainsId = JSON.stringify(data).includes(videoId);
    const hasPost = !!data.post;
    const hasAttachments = data.post?.attachments?.length > 0;
    
    if (urlContainsId || dataContainsId || hasPost) {
      console.log('%c🎯 发现相关请求!', 'color: #f59e0b; font-weight: bold;');
      console.log('  URL:', url);
      console.log('  URL 包含视频ID:', urlContainsId);
      console.log('  数据包含视频ID:', dataContainsId);
      console.log('  有 post 对象:', hasPost);
      console.log('  有 attachments:', hasAttachments);
      console.log('  数据结构:', Object.keys(data));
      
      if (hasPost) {
        console.log('  Post ID:', data.post.id);
        console.log('  Post Text:', data.post.text);
        if (hasAttachments) {
          console.log('  Attachment Kind:', data.post.attachments[0].kind);
        }
      }
      
      window.matchedRequests.push(requestInfo);
    }
    
  } catch (e) {
    // 非 JSON 响应
    window.allRequests.push({
      type: 'fetch',
      url: url,
      status: response.status,
      hasData: false
    });
  }
  
  return response;
};

// 拦截 XHR
const originalOpen = XMLHttpRequest.prototype.open;
const originalSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function(method, url, ...rest) {
  this._inspectUrl = url;
  this._inspectMethod = method;
  this._inspectStartTime = Date.now();
  return originalOpen.apply(this, [method, url, ...rest]);
};

XMLHttpRequest.prototype.send = function(...args) {
  this.addEventListener('load', function() {
    const duration = Date.now() - this._inspectStartTime;
    
    try {
      const data = JSON.parse(this.responseText);
      
      const requestInfo = {
        type: 'xhr',
        url: this._inspectUrl,
        method: this._inspectMethod,
        status: this.status,
        duration: duration,
        hasData: true,
        dataKeys: Object.keys(data),
        data: data
      };
      
      window.allRequests.push(requestInfo);
      
      // 检查是否包含视频 ID
      const urlContainsId = this._inspectUrl.includes(videoId);
      const dataContainsId = JSON.stringify(data).includes(videoId);
      const hasPost = !!data.post;
      const hasAttachments = data.post?.attachments?.length > 0;
      
      if (urlContainsId || dataContainsId || hasPost) {
        console.log('%c🎯 发现相关 XHR 请求!', 'color: #f59e0b; font-weight: bold;');
        console.log('  URL:', this._inspectUrl);
        console.log('  URL 包含视频ID:', urlContainsId);
        console.log('  数据包含视频ID:', dataContainsId);
        console.log('  有 post 对象:', hasPost);
        console.log('  有 attachments:', hasAttachments);
        
        window.matchedRequests.push(requestInfo);
      }
      
    } catch (e) {
      // 非 JSON 响应
      window.allRequests.push({
        type: 'xhr',
        url: this._inspectUrl,
        method: this._inspectMethod,
        status: this.status,
        hasData: false
      });
    }
  });
  
  return originalSend.apply(this, args);
};

console.log('%c✅ 检查器已设置', 'color: #10b981;');
console.log('%c💡 现在刷新页面 (Ctrl+R)', 'color: #667eea;');
console.log('%c💡 然后运行以下命令查看结果:', 'color: #667eea;');
console.log('');
console.log('  inspectHelpers.showAll()      - 查看所有请求');
console.log('  inspectHelpers.showMatched()  - 查看匹配的请求');
console.log('  inspectHelpers.showByUrl(keyword) - 按 URL 搜索');
console.log('  inspectHelpers.export()       - 导出数据');

// 辅助函数
window.inspectHelpers = {
  showAll: () => {
    console.log(`%c📊 共捕获 ${window.allRequests.length} 个请求`, 'color: #667eea; font-size: 14px;');
    console.table(window.allRequests.map(r => ({
      type: r.type,
      url: r.url?.substring(0, 80) || 'N/A',
      status: r.status,
      hasData: r.hasData,
      dataKeys: r.dataKeys?.join(', ') || 'N/A'
    })));
    return window.allRequests;
  },
  
  showMatched: () => {
    console.log(`%c🎯 找到 ${window.matchedRequests.length} 个匹配的请求`, 'color: #f59e0b; font-size: 14px;');
    
    if (window.matchedRequests.length === 0) {
      console.log('%c⚠️ 没有找到匹配的请求', 'color: #ef4444;');
      console.log('💡 提示: 刷新页面后再试');
      return [];
    }
    
    window.matchedRequests.forEach((req, index) => {
      console.group(`%c请求 #${index + 1}`, 'color: #667eea;');
      console.log('URL:', req.url);
      console.log('类型:', req.type);
      console.log('状态:', req.status);
      console.log('数据结构:', req.dataKeys);
      console.log('完整数据:', req.data);
      console.groupEnd();
    });
    
    return window.matchedRequests;
  },
  
  showByUrl: (keyword) => {
    const results = window.allRequests.filter(r => 
      r.url?.toLowerCase().includes(keyword.toLowerCase())
    );
    console.log(`%c🔍 找到 ${results.length} 个包含 "${keyword}" 的请求`, 'color: #667eea;');
    console.table(results.map(r => ({
      type: r.type,
      url: r.url,
      status: r.status,
      hasData: r.hasData
    })));
    return results;
  },
  
  export: () => {
    const dataStr = JSON.stringify({
      videoId: videoId,
      allRequests: window.allRequests,
      matchedRequests: window.matchedRequests
    }, null, 2);
    
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inspect-${videoId}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    console.log('%c✅ 数据已导出', 'color: #10b981;');
  },
  
  clear: () => {
    window.allRequests = [];
    window.matchedRequests = [];
    console.log('%c✅ 已清除所有记录', 'color: #10b981;');
  }
};

// 5 秒后自动显示结果
setTimeout(() => {
  if (window.matchedRequests.length > 0) {
    console.log(`%c🎉 自动检测到 ${window.matchedRequests.length} 个匹配的请求!`, 'color: #10b981; font-size: 14px;');
    console.log('%c💡 运行 inspectHelpers.showMatched() 查看详情', 'color: #667eea;');
  } else {
    console.log('%c⚠️ 5秒内未检测到匹配的请求', 'color: #f59e0b;');
    console.log('%c💡 请刷新页面 (Ctrl+R) 后再试', 'color: #667eea;');
    console.log(`%c💡 或运行 inspectHelpers.showAll() 查看所有 ${window.allRequests.length} 个请求`, 'color: #667eea;');
  }
}, 5000);
