// Sora Video Monitor - 数据收集器
console.log('=== Sora Collector 启动 ===');

class SoraCollector {
  constructor() {
    this.videos = { published: [], generating: [], unpublished: [] };
    this.logs = [];
    this.currentPage = window.location.pathname;
    this.accountInfo = null;
    console.log('Collector 初始化，当前页面:', this.currentPage);
    this.init();
  }

  log(msg, type = 'info') {
    const time = new Date().toLocaleTimeString();
    this.logs.push({ time, type, message: msg });
    console.log(`[${time}] ${msg}`);
    this.saveLogs();
  }

  init() {
    this.log('初始化收集器');
    
    // 立即发送测试日志到后端
    this.sendTestLog('Content script 已加载');
    
    this.setupInterceptors();
    
    // 获取账号信息
    this.fetchAccountInfo();
    
    const pageType = this.getPageType();
    
    // 只在 profile 和 drafts 页面收集数据
    if (pageType === 'profile' || pageType === 'drafts') {
      this.log(`在 ${pageType} 页面，启动数据收集`);
      
      // 立即收集当前页面数据
      setTimeout(() => this.collectCurrentPage(), 1000);
      
      // 定期收集
      setInterval(() => this.collectCurrentPage(), 15000);
    } else {
      this.log('在 explore 页面，不自动收集数据');
    }
    
    // 监听来自 background 的指令
    this.listenForData();
  }
  
  async sendTestLog(message) {
    try {
      const result = await chrome.storage.local.get(['backendUrl']);
      const backendUrl = result.backendUrl || 'http://localhost:8000';
      
      await fetch(`${backendUrl}/v1/debug/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: message,
          url: window.location.href,
          timestamp: new Date().toISOString()
        })
      });
    } catch (error) {
      console.error('发送测试日志失败:', error);
    }
  }

  setupInterceptors() {
    if (window._intercepted) return;
    
    const self = this;
    const origFetch = window.fetch;
    
    window.fetch = async function(...args) {
      const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
      const response = await origFetch.apply(this, args);
      const clone = response.clone();
      
      try {
        if (url && url.includes('sora.chatgpt.com')) {
          const ct = response.headers.get('content-type') || '';
          if (ct.includes('json')) {
            const data = await clone.json();
            self.log('拦截API: ' + url, 'network');
            self.parseAPI(data, url);
          }
        }
      } catch (e) {}
      
      return response;
    };
    
    window._intercepted = true;
    this.log('拦截器已安装');
  }

  async fetchAccountInfo() {
    try {
      this.log('获取账号信息...');
      const response = await fetch('https://sora.chatgpt.com/api/auth/session');
      
      if (response.ok) {
        const data = await response.json();
        this.accountInfo = {
          email: data.user?.email || null,
          name: data.user?.name || null,
          id: data.user?.id || null,
          image: data.user?.image || null
        };
        
        this.log(`账号信息: ${this.accountInfo.email || this.accountInfo.name || 'Unknown'}`);
        
        // 保存到 storage
        chrome.storage.local.set({ 
          soraAccountInfo: this.accountInfo 
        });
        
        // 发送到 background
        chrome.runtime.sendMessage({
          type: 'ACCOUNT_INFO',
          account: this.accountInfo
        }).catch(() => {});
        
      } else {
        this.log('获取账号信息失败: ' + response.status, 'warning');
      }
    } catch (error) {
      this.log('获取账号信息出错: ' + error.message, 'error');
    }
  }

  collectCurrentPage() {
    const pageType = this.getPageType();
    this.log(`🔍 开始收集 - 当前页面类型: ${pageType}`);
    this.log(`   当前 URL: ${window.location.href}`);
    
    // 只收集 profile 和 drafts 页面，忽略 explore
    if (pageType !== 'profile' && pageType !== 'drafts') {
      this.log('⏭️ 跳过 explore 页面，不收集数据');
      return;
    }
    
    this.log(`📊 收集 ${pageType} 页面数据`);
    
    // 清空旧数据
    this.videos = { published: [], generating: [], unpublished: [] };
    
    // 根据页面类型使用不同的选择器
    let links;
    let selector;
    if (pageType === 'profile') {
      // profile 页面：已发布视频使用 /p/s_xxx 格式
      selector = 'a[href*="/p/s_"]';
      links = document.querySelectorAll(selector);
      this.log(`🔎 使用选择器: ${selector}`);
      this.log(`✅ 找到 ${links.length} 个已发布视频链接`);
    } else {
      // drafts 页面：草稿视频使用 /d/gen_xxx 格式
      selector = 'a[href*="/d/gen_"]';
      links = document.querySelectorAll(selector);
      this.log(`🔎 使用选择器: ${selector}`);
      this.log(`✅ 找到 ${links.length} 个草稿视频链接`);
    }
    
    // 如果没有找到链接，尝试其他方法
    if (links.length === 0) {
      this.log(`⚠️ 未找到视频链接，尝试查找所有链接...`);
      const allLinks = document.querySelectorAll('a[href]');
      this.log(`   页面共有 ${allLinks.length} 个链接`);
      
      // 显示前10个链接作为调试信息
      let relevantCount = 0;
      allLinks.forEach((link, i) => {
        if (i < 10 || link.href.includes('/p/') || link.href.includes('/d/')) {
          this.log(`   链接 ${i}: ${link.href}`);
          if (link.href.includes('/p/') || link.href.includes('/d/')) {
            relevantCount++;
          }
        }
      });
      
      this.log(`   找到 ${relevantCount} 个相关链接（包含 /p/ 或 /d/）`);
      
      // 仍然通知 background
      chrome.runtime.sendMessage({
        type: 'COLLECTION_COMPLETE',
        page: pageType,
        count: 0
      }).catch(() => {});
      
      // 即使没有视频，也发送到后端（保持账号信息更新）
      this.sendToBackend();
      return;
    }
    
    // 使用 Set 去重
    const seenIds = new Set();
    
    links.forEach((link, index) => {
      const href = link.href;
      
      // 尝试获取视频ID
      const id = this.extractId(href);
      if (!id) {
        this.log(`⚠️ 无法提取 ID: ${href}`);
        return;
      }
      
      // 去重检查
      if (seenIds.has(id)) {
        this.log(`⏭️ 跳过重复视频: ${id}`);
        return;
      }
      seenIds.add(id);
      
      const videoData = {
        id,
        url: href,
        prompt: null, // 提示词由 plug-renwu 插件通过 API 拦截获取
        status: pageType === 'profile' ? 'published' : 'unpublished',
        source: pageType,
        timestamp: Date.now()
      };
      
      this.log(`✅ 收集视频 ${index + 1}: ${id} (${videoData.status})`);
      
      // 添加到本地数据
      if (pageType === 'profile') {
        this.videos.published.push(videoData);
      } else {
        this.videos.unpublished.push(videoData);
      }
      
      // 发送到 background
      chrome.runtime.sendMessage({
        type: 'ADD_VIDEO',
        video: videoData
      }).catch(() => {});
    });
    
    this.log(`📈 收集完成: ${seenIds.size} 个视频`);
    
    // 查找生成进度（只在 drafts 页面）
    if (pageType === 'drafts') {
      this.collectGenerating();
    }
    
    // 保存到 storage
    this.saveVideos();
    
    // 发送到后端
    this.sendToBackend();
    
    // 通知 background 收集完成
    chrome.runtime.sendMessage({
      type: 'COLLECTION_COMPLETE',
      page: pageType,
      count: seenIds.size
    }).catch(() => {});
  }
  
  collectGenerating() {
    this.log('查找生成中的视频');
    
    // 方法1: 查找包含百分比的元素
    const all = document.querySelectorAll('*');
    let found = 0;
    const foundIds = new Set();
    
    all.forEach(el => {
      const text = el.textContent || '';
      if (text.length < 300 && (text.includes('%') || text.includes('生成') || text.includes('Generating'))) {
        const progress = this.extractProgress(text);
        if (progress !== null && progress > 0 && progress < 100) {
          // 尝试找到关联的链接（支持两种格式）
          const parent = el.closest('div, article, section');
          const link = parent?.querySelector('a[href*="/p/s_"], a[href*="/d/gen_"]');
          const id = link ? this.extractId(link.href) : null;
          
          // 避免重复
          const uniqueId = id || `gen_${progress}_${text.substring(0, 20)}`;
          if (foundIds.has(uniqueId)) return;
          foundIds.add(uniqueId);
          
          found++;
          
          const genData = {
            id: id || `gen_${Date.now()}_${found}`,
            url: link?.href || null,
            progress,
            status: 'generating',
            source: 'drafts',
            timestamp: Date.now()
          };
          
          this.log(`生成中: ${progress}% (ID: ${genData.id})`);
          
          // 添加到本地数据
          this.videos.generating.push(genData);
          
          // 发送到 background
          chrome.runtime.sendMessage({
            type: 'ADD_VIDEO',
            video: genData
          }).catch(() => {});
        }
      }
    });
    
    // 方法2: 查找所有视频卡片，检查是否有进度条
    const cards = document.querySelectorAll('[class*="card"], [class*="item"], [class*="video"]');
    this.log(`检查 ${cards.length} 个可能的视频卡片`);
    
    cards.forEach(card => {
      const progressBar = card.querySelector('[role="progressbar"], [class*="progress"]');
      if (progressBar) {
        const text = card.textContent || '';
        const progress = this.extractProgress(text);
        const link = card.querySelector('a[href*="/p/s_"], a[href*="/d/gen_"]');
        const id = link ? this.extractId(link.href) : null;
        
        if (progress !== null && progress > 0 && progress < 100) {
          const uniqueId = id || `gen_prog_${progress}`;
          if (foundIds.has(uniqueId)) return;
          foundIds.add(uniqueId);
          
          found++;
          
          const genData = {
            id: id || `gen_${Date.now()}_${found}`,
            url: link?.href || null,
            progress,
            status: 'generating',
            source: 'drafts_progressbar',
            timestamp: Date.now()
          };
          
          this.log(`进度条: ${progress}% (ID: ${genData.id})`);
          
          // 添加到本地数据
          this.videos.generating.push(genData);
          
          // 发送到 background
          chrome.runtime.sendMessage({
            type: 'ADD_VIDEO',
            video: genData
          }).catch(() => {});
        }
      }
    });
    
    this.log(`总共找到 ${found} 个生成中视频`);
  }

  getPageType() {
    // 精确匹配，避免 /d/gen_xxx 被误判为 /drafts
    if (this.currentPage === '/profile' || this.currentPage.startsWith('/profile/')) return 'profile';
    if (this.currentPage === '/drafts') return 'drafts';
    if (this.currentPage === '/explore' || this.currentPage.startsWith('/explore/')) return 'explore';
    
    // 视频详情页
    if (this.currentPage.match(/^\/(p|d)\/[a-z0-9_]+$/)) return 'video';
    
    return 'unknown';
  }

  parseAPI(data, url) {
    let videos = [];
    
    if (Array.isArray(data)) {
      videos = data;
    } else if (data.videos) {
      videos = data.videos;
    } else if (data.items) {
      videos = data.items;
    } else if (data.data) {
      videos = Array.isArray(data.data) ? data.data : [data.data];
    }
    
    videos.forEach(v => {
      if (!v) return;
      const id = v.id || v.video_id || v.videoId;
      if (!id || !id.startsWith('s_')) return;
      
      const videoData = {
        id,
        url: v.url || `https://sora.chatgpt.com/p/${id}`,
        status: v.status || 'unknown',
        progress: v.progress || null,
        source: 'api',
        timestamp: Date.now()
      };
      
      chrome.runtime.sendMessage({
        type: 'ADD_VIDEO',
        video: videoData
      });
    });
  }

  listenForData() {
    chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
      if (req.type === 'GET_VIDEOS') {
        sendResponse(this.videos);
      } else if (req.type === 'GET_LOGS') {
        sendResponse(this.logs);
      } else if (req.type === 'COLLECT_NOW') {
        this.log('收到手动收集命令');
        this.collectCurrentPage();
        sendResponse({ success: true });
      }
      return true;
    });
  }

  extractId(url) {
    // 匹配已发布视频: /p/s_xxx
    let m = url.match(/\/p\/(s_[a-f0-9]+)/);
    if (m) return m[1];
    
    // 匹配草稿视频: /d/gen_xxx
    m = url.match(/\/d\/(gen_[a-z0-9]+)/);
    if (m) return m[1];
    
    return null;
  }

  extractProgress(text) {
    const m = text.match(/(\d+)%/);
    return m ? parseInt(m[1]) : null;
  }

  saveLogs() {
    chrome.storage.local.set({ soraLogs: this.logs.slice(-100) });
  }
  
  saveVideos() {
    chrome.storage.local.set({ 
      soraVideos: this.videos,
      lastUpdate: new Date().toISOString()
    });
  }
  
  async sendToBackend() {
    try {
      // 从 storage 获取后端 API 地址
      const result = await chrome.storage.local.get(['backendUrl']);
      const backendUrl = result.backendUrl || 'http://localhost:8000';
      
      const statsData = {
        totalVideos: this.videos.published.length + this.videos.generating.length + this.videos.unpublished.length,
        publishedVideos: this.videos.published.length,
        generatingVideos: this.videos.generating.length,
        unpublishedVideos: this.videos.unpublished.length,
        videos: {
          published: this.videos.published,
          generating: this.videos.generating,
          unpublished: this.videos.unpublished
        },
        account: this.accountInfo,
        lastUpdate: new Date().toISOString()
      };
      
      this.log(`📤 发送数据到后端: ${backendUrl}`);
      this.log(`   总视频: ${statsData.totalVideos}, 已发布: ${statsData.publishedVideos}, 生成中: ${statsData.generatingVideos}, 未发布: ${statsData.unpublishedVideos}`);
      this.log(`   账号: ${this.accountInfo?.email || 'Unknown'}`);
      
      const response = await fetch(`${backendUrl}/v1/videos/stats`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(statsData)
      });
      
      if (response.ok) {
        const result = await response.json();
        this.log('✅ 数据发送成功');
      } else {
        const errorText = await response.text();
        this.log(`⚠️ 数据发送失败: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      this.log(`❌ 发送数据到后端失败: ${error.message}`);
    }
  }

  getVideos() { return this.videos; }
  getLogs() { return this.logs; }
}

const collector = new SoraCollector();
window.soraCollector = collector;

console.log('=== Sora Collector 就绪 ===');
