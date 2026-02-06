// 注入到页面上下文的拦截器脚本
// 此脚本运行在页面的 JavaScript 上下文中，可以拦截页面的 fetch/XHR 请求

(function() {
  console.log('📡 页面拦截器已注入');
  
  // 保存原始函数
  const originalFetch = window.fetch;
  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  
  // 🔑 保存捕获到的 Authorization token
  let authToken = null;
  
  // 🚫 禁止视频加载的配置
  const BLOCK_VIDEO_LOADING = true; // 设置为 true 禁止视频加载
  
  // 判断是否为视频资源请求
  function isVideoResource(url) {
    // 匹配视频文件扩展名
    if (/\.(mp4|webm|m3u8|ts|mov)(\?|$)/i.test(url)) {
      return true;
    }
    
    // 匹配视频流 URL 模式
    if (/video|stream|media|blob:http/i.test(url)) {
      return true;
    }
    
    // 匹配 Sora 视频 CDN
    if (/cdn.*\.(mp4|webm)/i.test(url)) {
      return true;
    }
    
    return false;
  }
  
  // 拦截 Fetch
  window.fetch = async function(...args) {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || 'unknown';
    
    // 🚫 如果是视频资源，阻止加载
    if (BLOCK_VIDEO_LOADING && isVideoResource(url)) {
      console.log('🚫 已阻止视频加载:', url);
      // 返回一个空的响应，避免报错
      return new Response(null, {
        status: 200,
        statusText: 'OK (Blocked by extension)',
        headers: { 'Content-Type': 'video/mp4' }
      });
    }
    
    console.log('📡 Fetch 请求:', url);
    
    // 🔑 捕获 Authorization header
    const options = args[1] || {};
    if (options.headers) {
      const headers = options.headers;
      
      // 检查是否有 Authorization header
      if (headers instanceof Headers) {
        const auth = headers.get('Authorization');
        if (auth && auth.startsWith('Bearer ')) {
          authToken = auth;
          console.log('🔑 捕获到 Authorization token');
        }
      } else if (typeof headers === 'object') {
        const auth = headers['Authorization'] || headers['authorization'];
        if (auth && auth.startsWith('Bearer ')) {
          authToken = auth;
          console.log('🔑 捕获到 Authorization token');
        }
      }
    }
    
    const response = await originalFetch.apply(this, args);
    
    // 克隆响应以便读取
    const clonedResponse = response.clone();
    
    // 检查是否需要捕获
    const shouldCapture = /\/backend\/(project_y|nf)\//.test(url);
    
    if (shouldCapture) {
      try {
        const data = await clonedResponse.json();
        console.log('📦 捕获到响应:', url);
        
        // 通过自定义事件发送到 content script
        window.dispatchEvent(new CustomEvent('soraApiCaptured', {
          detail: { url, data }
        }));
      } catch (error) {
        // 忽略非 JSON 响应
      }
    }
    
    return response;
  };
  
  // 拦截 XMLHttpRequest
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._captureUrl = url;
    this._captureMethod = method;
    
    // 🚫 如果是视频资源，标记为阻止
    if (BLOCK_VIDEO_LOADING && isVideoResource(url)) {
      this._blockVideo = true;
      console.log('🚫 已阻止视频加载 (XHR):', url);
    } else {
      console.log('📡 XHR 请求:', method, url);
    }
    
    return originalOpen.apply(this, [method, url, ...rest]);
  };
  
  const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
    // 🔑 捕获 Authorization header
    if (header.toLowerCase() === 'authorization' && value.startsWith('Bearer ')) {
      authToken = value;
      console.log('🔑 捕获到 Authorization token (XHR)');
    }
    return originalSetRequestHeader.apply(this, arguments);
  };
  
  XMLHttpRequest.prototype.send = function(...args) {
    const xhr = this;
    
    // 🚫 如果标记为阻止视频，直接返回空响应
    if (xhr._blockVideo) {
      // 模拟成功响应
      setTimeout(() => {
        Object.defineProperty(xhr, 'readyState', { value: 4, writable: false });
        Object.defineProperty(xhr, 'status', { value: 200, writable: false });
        Object.defineProperty(xhr, 'statusText', { value: 'OK (Blocked)', writable: false });
        Object.defineProperty(xhr, 'responseText', { value: '', writable: false });
        
        const event = new Event('load');
        xhr.dispatchEvent(event);
      }, 0);
      return;
    }
    
    this.addEventListener('load', function() {
      const shouldCapture = /\/backend\/(project_y|nf)\//.test(xhr._captureUrl);
      
      if (shouldCapture) {
        try {
          const data = JSON.parse(xhr.responseText);
          console.log('📦 捕获到 XHR 响应:', xhr._captureUrl);
          
          // 通过自定义事件发送到 content script
          window.dispatchEvent(new CustomEvent('soraApiCaptured', {
            detail: { url: xhr._captureUrl, data }
          }));
        } catch (error) {
          // 忽略非 JSON 响应
        }
      }
    });
    
    return originalSend.apply(this, args);
  };
  
  console.log('✅ 页面拦截器设置完成');
  
  // 🚫 阻止页面上的 <video> 标签加载
  if (BLOCK_VIDEO_LOADING) {
    console.log('🚫 启用视频标签拦截...');
    
    // 拦截现有的 video 标签
    function blockVideoElements() {
      const videos = document.querySelectorAll('video');
      videos.forEach(video => {
        if (!video._blocked) {
          video._blocked = true;
          video.preload = 'none'; // 禁止预加载
          video.autoplay = false; // 禁止自动播放
          video.src = ''; // 清空 src
          
          // 移除 source 标签
          const sources = video.querySelectorAll('source');
          sources.forEach(source => source.remove());
          
          console.log('🚫 已阻止 video 标签加载');
        }
      });
    }
    
    // 立即执行一次
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', blockVideoElements);
    } else {
      blockVideoElements();
    }
    
    // 监听 DOM 变化，拦截新添加的 video 标签
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) { // Element node
            // 检查节点本身是否是 video
            if (node.tagName === 'VIDEO' && !node._blocked) {
              node._blocked = true;
              node.preload = 'none';
              node.autoplay = false;
              node.src = '';
              console.log('🚫 已阻止新添加的 video 标签');
            }
            
            // 检查子节点中的 video
            const videos = node.querySelectorAll?.('video');
            videos?.forEach(video => {
              if (!video._blocked) {
                video._blocked = true;
                video.preload = 'none';
                video.autoplay = false;
                video.src = '';
                console.log('🚫 已阻止新添加的 video 标签（子节点）');
              }
            });
          }
        });
      });
    });
    
    // 开始观察
    if (document.documentElement) {
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true
      });
    }
    
    console.log('✅ 视频标签拦截已启用');
  }
})();
