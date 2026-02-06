// Sora 视频抓包内容脚本
console.log('🎬 Sora 视频抓包内容脚本已加载');
console.log('📍 当前页面:', window.location.href);

// 配置
let config = {
  enabled: true,
  autoSend: true
};

// 当前登录用户的 user_id（从 /backend/project_y/v2/me 获取）
let currentUserId = null;

// 立即设置网络拦截器（在任何其他代码之前）
setupNetworkInterceptors();

// 如果是首次加载，提示用户刷新
if (document.readyState === 'loading') {
  console.log('💡 提示: 如果没有看到请求日志，请刷新页面 (Ctrl+R)');
}

// 获取配置
chrome.runtime.sendMessage({ type: 'GET_CONFIG' }, (response) => {
  if (response && response.config) {
    config = response.config;
    console.log('⚙️ 获取配置:', config);
  }
});

// 检查是否在视频详情页
function isVideoDetailPage() {
  return /\/p\/s_[a-f0-9]+/.test(window.location.pathname);
}

// 从 URL 中提取视频 ID
function extractVideoIdFromUrl(url) {
  const match = url.match(/\/p\/(s_[a-f0-9]+)/);
  return match ? match[1] : null;
}

// 如果在视频详情页，主动请求数据
if (isVideoDetailPage()) {
  const videoId = extractVideoIdFromUrl(window.location.pathname);
  console.log('🎯 检测到视频详情页，视频ID:', videoId);
  
  // 延迟一点，等待页面加载
  setTimeout(() => {
    fetchVideoData(videoId);
  }, 500);
}

// 监听 URL 变化（SPA 页面）
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    console.log('🔄 URL 变化:', url);
    
    // 检查是否是视频详情页
    if (isVideoDetailPage()) {
      const videoId = extractVideoIdFromUrl(url);
      console.log('🎯 检测到新的视频详情页，视频ID:', videoId);
      
      setTimeout(() => {
        fetchVideoData(videoId);
      }, 500);
    }
  }
}).observe(document, { subtree: true, childList: true });

// 🆕 直接请求 API 获取视频数据
// 注意: 这个函数发起的请求会被拦截器捕获，所以不需要在这里再次调用 handleCapturedData
async function fetchVideoData(videoId) {
  console.log('🚀 直接请求 API 获取视频数据...');
  
  const apiUrl = `https://sora.chatgpt.com/backend/project_y/post/${videoId}`;
  console.log('📡 请求 URL:', apiUrl);
  
  try {
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('✅ 成功获取视频数据:', data);
    
    if (data.post && data.post.id === videoId) {
      console.log('🎬 验证通过: 视频数据匹配');
      // 不需要在这里调用 handleCapturedData，因为拦截器会自动处理
    } else {
      console.log('⚠️ 数据验证失败: 视频ID不匹配');
    }
    
  } catch (error) {
    console.error('❌ 请求失败:', error);
  }
}

// 🔧 设置网络拦截器（监听来自注入脚本的事件）
function setupNetworkInterceptors() {
  console.log('🔧 正在设置网络拦截器...');
  
  // 监听来自注入脚本的自定义事件
  window.addEventListener('soraApiCaptured', (event) => {
    const { url, data } = event.detail;
    console.log('📥 Content script 收到捕获数据:', url);
    handleCapturedData(url, data);
  });
  
  console.log('✅ 网络拦截器已设置');
  console.log('💡 现在会持续监听所有网络请求');
}

// 🆕 从页面数据中提取视频信息
function extractFromPageData(videoId) {
  console.log('🔍 尝试从页面数据中提取视频信息...');
  
  let extracted = false;
  
  // 方法 1: 监听 self.__next_f
  const checkNextF = () => {
    if (window.self && window.self.__next_f) {
      console.log('✅ 找到 __next_f 对象');
      
      const originalPush = Array.prototype.push;
      window.self.__next_f.push = function(...args) {
        if (!extracted && args[0] && args[0][1]) {
          const content = String(args[0][1]);
          if (content.includes(videoId) && content.includes('"post"')) {
            console.log('🎯 在 __next_f 中发现视频数据!');
            tryExtractJSON(content, '__next_f');
          }
        }
        return originalPush.apply(this, args);
      };
      
      // 检查已有数据
      if (window.self.__next_f.length > 0) {
        console.log(`📦 检查已有的 ${window.self.__next_f.length} 条数据`);
        window.self.__next_f.forEach((item, index) => {
          if (!extracted && item && item[1]) {
            const content = String(item[1]);
            if (content.includes(videoId) && content.includes('"post"')) {
              console.log(`🎯 在已有数据 [${index}] 中发现视频数据!`);
              tryExtractJSON(content, `__next_f[${index}]`);
            }
          }
        });
      }
    }
  };
  
  // 方法 2: 监听 script 标签的添加
  const scriptObserver = new MutationObserver((mutations) => {
    if (extracted) return;
    
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeName === 'SCRIPT') {
          const content = node.textContent || node.innerHTML;
          if (content.includes(videoId) && content.includes('"post"')) {
            console.log('🎯 在新添加的 script 标签中发现视频数据!');
            tryExtractJSON(content, 'new_script');
          }
        }
      });
    });
  });
  
  // 方法 3: 检查现有的 script 标签
  const checkExistingScripts = () => {
    if (extracted) return;
    
    console.log('📦 检查现有的 script 标签...');
    const scripts = document.querySelectorAll('script');
    console.log(`🔍 找到 ${scripts.length} 个 script 标签`);
    
    for (let i = 0; i < scripts.length; i++) {
      if (extracted) break;
      
      const script = scripts[i];
      const content = script.textContent || script.innerHTML;
      
      if (content.includes(videoId) && content.includes('"post"')) {
        console.log(`🎯 在 script[${i}] 中发现视频数据!`);
        tryExtractJSON(content, `script[${i}]`);
      }
    }
  };
  
  // 尝试提取 JSON
  function tryExtractJSON(content, source) {
    if (extracted) return;
    
    try {
      // 方法 A: 查找完整的 {post:..., profile:...} 对象
      const patterns = [
        /\{"post":\{[^]*?"profile":\{[^]*?\}\}/g,
        /\{[^]*?"post":\{[^]*?\}[^]*?"profile":\{[^]*?\}\}/g,
      ];
      
      for (const pattern of patterns) {
        const matches = content.match(pattern);
        if (matches) {
          console.log(`📝 找到 ${matches.length} 个可能的 JSON 对象`);
          
          for (let i = 0; i < matches.length; i++) {
            if (extracted) break;
            
            try {
              // 清理字符串
              let jsonStr = matches[i];
              
              // 移除转义字符
              jsonStr = jsonStr.replace(/\\"/g, '"');
              jsonStr = jsonStr.replace(/\\n/g, '');
              jsonStr = jsonStr.replace(/\\t/g, '');
              
              const data = JSON.parse(jsonStr);
              
              if (data.post && data.post.id === videoId) {
                console.log(`✅ 成功解析视频数据 (来源: ${source}, 匹配: ${i})`);
                console.log('📦 数据:', data);
                extracted = true;
                handleCapturedData(source, data);
                return;
              }
            } catch (e) {
              // 继续尝试下一个
            }
          }
        }
      }
    } catch (e) {
      console.log('⚠️ 提取失败:', e.message);
    }
  }
  
  // 立即执行检查
  checkNextF();
  checkExistingScripts();
  
  // 开始监听新的 script 标签
  if (document.documentElement) {
    scriptObserver.observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  }
  
  // 延迟检查（等待页面加载）
  setTimeout(() => {
    if (!extracted) {
      console.log('🔄 延迟检查...');
      checkNextF();
      checkExistingScripts();
    }
  }, 1000);
  
  setTimeout(() => {
    if (!extracted) {
      console.log('🔄 最后一次检查...');
      checkNextF();
      checkExistingScripts();
    }
  }, 3000);
  
  // 5秒后停止监听
  setTimeout(() => {
    scriptObserver.disconnect();
    if (!extracted) {
      console.log('⚠️ 未能从页面数据中提取视频信息');
      console.log('💡 提示: 请刷新页面重试');
    }
  }, 5000);
}

// 注意: 拦截器已在文件开头通过 setupNetworkInterceptors() 设置
// 这里不需要重复设置

// 判断是否应该捕获该 URL
function shouldCaptureUrl(url) {
  // 移除 config.enabled 检查，让拦截器始终工作
  // config 会在后面异步加载，不应该阻止拦截
  
  // 匹配 Sora 相关的 API 端点
  const patterns = [
    // 🎯 核心模式：backend/project_y/post/视频ID
    /\/backend\/project_y\/post\/s_[a-f0-9]+/,
    
    // 🆕 账号信息（实际路径）
    /\/backend\/project_y\/v2\/me$/,
    /\/backend\/project_y\/me$/,  // 保留旧路径以防万一
    
    // 🆕 账号可用次数（实际路径）
    /\/backend\/nf\/check/,
    /\/backend\/project_y\/check/,  // 保留旧路径以防万一
    
    // 🆕 创建视频
    /\/backend\/project_y\/create/,
    
    // 🆕 视频生成进度
    /\/backend\/project_y\/v2/,
    
    // 🆕 草稿列表（drafts）
    /\/backend\/project_y\/profile\/drafts/,
    
    // 🆕 已发布视频列表（profile_feed）
    /\/backend\/project_y\/profile_feed/,
    
    // 视频详情页 API
    /\/p\/s_[a-f0-9]+/,
    /\/posts\/s_[a-f0-9]+/,
    /\/post\/s_[a-f0-9]+/,
    
    // Feed 和列表 API
    /sora\.chatgpt\.com\/.*\/feed/,
    /chatgpt\.com\/.*\/feed/,
    /sora\.chatgpt\.com\/.*\/posts/,
    /chatgpt\.com\/.*\/posts/,
    
    // Backend API
    /sora\.chatgpt\.com\/backend-api/,
    /chatgpt\.com\/backend-api/,
    /\/backend\/project_y\//,
    /\/backend\/nf\//,  // 新增：nf 路径
    
    // 其他可能的端点
    /api\.sora\.com/,
    /\/api\/.*\/posts/,
    /\/api\/.*\/videos/
  ];
  
  const shouldCapture = patterns.some(pattern => pattern.test(url));
  
  if (shouldCapture) {
    console.log('🎯 匹配到需要捕获的 URL:', url);
  }
  
  return shouldCapture;
}

// 🆕 识别 API 类型
function identifyApiType(url) {
  // 用户信息（实际路径）
  if (/\/backend\/project_y\/v2\/me$/.test(url)) return 'USER_INFO';
  if (/\/backend\/project_y\/me$/.test(url)) return 'USER_INFO';
  
  // 配额信息（实际路径）
  if (/\/backend\/nf\/check/.test(url)) return 'QUOTA';
  if (/\/backend\/project_y\/check/.test(url)) return 'QUOTA';
  
  // 创建视频（实际路径是 /backend/nf/create）
  if (/\/backend\/nf\/create$/.test(url)) return 'CREATE_VIDEO';
  if (/\/backend\/project_y\/create$/.test(url)) return 'CREATE_VIDEO';
  
  // 视频进度查询（实际路径是 /backend/nf/pending/v2）
  if (/\/backend\/nf\/pending/.test(url)) return 'VIDEO_PROGRESS';
  if (/\/backend\/project_y\/v2/.test(url) && !/\/v2\/me$/.test(url)) return 'VIDEO_PROGRESS';
  
  // 草稿列表
  if (/\/backend\/project_y\/profile\/drafts/.test(url)) return 'DRAFTS_LIST';
  
  // 已发布视频列表
  if (/\/backend\/project_y\/profile_feed/.test(url)) return 'PUBLISHED_LIST';
  
  // 视频详情
  if (/\/backend\/project_y\/post\/s_[a-f0-9]+/.test(url)) return 'VIDEO_DETAIL';
  
  return 'OTHER';
}

// 处理捕获的数据
function handleCapturedData(url, data) {
  const apiType = identifyApiType(url);
  
  console.log('📦 捕获到数据:', url);
  console.log('📦 API 类型:', apiType);
  console.log('📦 数据结构:', Object.keys(data));
  
  // 🔍 调试：如果数据包含 task_type 和 id，可能是创建视频
  if (data.id && data.task_type && apiType === 'OTHER') {
    console.log('⚠️ 检测到可能是创建视频的响应，但 API 类型识别为 OTHER');
    console.log('⚠️ URL:', url);
    console.log('⚠️ 数据:', data);
  }
  
  // 根据 API 类型处理数据
  switch (apiType) {
    case 'USER_INFO':
      handleUserInfo(data);
      break;
    
    case 'QUOTA':
      handleQuota(data);
      break;
    
    case 'CREATE_VIDEO':
      handleCreateVideo(data);
      break;
    
    case 'VIDEO_PROGRESS':
      handleVideoProgress(data);
      break;
    
    case 'DRAFTS_LIST':
      handleDraftsList(data);
      break;
    
    case 'PUBLISHED_LIST':
      handlePublishedList(data);
      break;
    
    case 'VIDEO_DETAIL':
      handleVideoDetail(data);
      break;
    
    default:
      // 🔍 检查是否是创建视频的响应（通过数据结构判断）
      if (data.id && data.task_type && data.rate_limit_and_credit_balance) {
        console.log('🎬 检测到创建视频响应（通过数据结构识别）');
        handleCreateVideo(data);
        return;
      }
      
      // 🔍 检查是否是视频进度数组（通过数据结构判断）
      if (Array.isArray(data) && data.length > 0 && data[0].id && data[0].task_type && data[0].status) {
        console.log('📈 检测到视频进度响应（通过数据结构识别）');
        handleVideoProgress(data);
        return;
      }
      
      // 检查是否为视频数据
      if (isValidVideoData(data)) {
        if (isCurrentUserVideo(data)) {
          console.log('✅ 发现有效的视频数据（当前用户）');
          console.log('  - Post ID:', data.post.id);
          sendToBackground(data);
        }
      } else if (data.items && Array.isArray(data.items)) {
        // 处理列表数据
        console.log(`📋 处理列表数据，共 ${data.items.length} 项`);
        let capturedCount = 0;
        data.items.forEach((item, index) => {
          if (isValidVideoData(item)) {
            if (isCurrentUserVideo(item)) {
              console.log(`✅ 发现有效的视频数据（列表项 ${index + 1}，当前用户）`);
              console.log('  - Post ID:', item.post.id);
              sendToBackground(item);
              capturedCount++;
            }
          }
        });
        console.log(`📊 列表处理完成: ${capturedCount}/${data.items.length} 个视频属于当前用户`);
      } else if (data.post) {
        // 直接包含 post 对象
        if (isCurrentUserVideo(data)) {
          console.log('✅ 发现包含 post 的数据（当前用户）');
          console.log('  - Post ID:', data.post.id);
          sendToBackground(data);
        }
      } else {
        console.log('⚠️ 数据格式不匹配，跳过');
      }
  }
}

// 🆕 处理用户信息
function handleUserInfo(data) {
  console.log('👤 处理用户信息:', data);
  
  // 提取 my_info 和 profile 数据
  const myInfo = data.my_info || {};
  const profile = data.profile || myInfo.profile || {};
  
  // 🆕 保存当前用户的 user_id 和 email，用于过滤视频和关联配额
  currentUserId = profile.user_id || data.user_id;
  window.currentUserId = currentUserId;
  window.currentUserEmail = myInfo.email || data.email;
  console.log('✅ 当前用户 ID:', currentUserId);
  console.log('✅ 当前用户邮箱:', window.currentUserEmail);
  
  const userInfo = {
    type: 'USER_INFO',
    // 基本信息
    user_id: profile.user_id || data.user_id,
    email: myInfo.email || data.email,
    username: profile.username || data.username,
    display_name: profile.display_name,
    
    // 个人资料
    profile_picture_url: profile.profile_picture_url || data.profile_picture_url,
    cover_photo_url: profile.cover_photo_url,
    description: profile.description,
    location: profile.location,
    website: profile.website,
    birthday: profile.birthday,
    
    // 验证信息
    verified: profile.verified || data.verified,
    is_phone_number_verified: myInfo.is_phone_number_verified,
    is_underage: myInfo.is_underage,
    
    // 计划和权限
    plan_type: profile.plan_type || data.plan_type,
    
    // 邀请信息
    invite_code: myInfo.invite_code,
    invite_url: myInfo.invite_url,
    invites_remaining: myInfo.invites_remaining,
    num_redemption_gens: myInfo.num_redemption_gens,
    
    // 统计信息
    follower_count: profile.follower_count,
    following_count: profile.following_count,
    post_count: profile.post_count,
    reply_count: profile.reply_count,
    likes_received_count: profile.likes_received_count,
    remix_count: profile.remix_count,
    cameo_count: profile.cameo_count,
    character_count: profile.character_count,
    
    // 设置
    sora_who_can_message_me: profile.sora_who_can_message_me,
    chatgpt_who_can_message_me: profile.chatgpt_who_can_message_me,
    can_message: profile.can_message,
    can_cameo: profile.can_cameo,
    calpico_is_enabled: profile.calpico_is_enabled,
    
    // 时间戳
    signup_date: myInfo.signup_date,
    created_at: profile.created_at || data.created_at,
    updated_at: profile.updated_at,
    captured_at: new Date().toISOString()
  };
  
  console.log('✅ 用户信息已提取:', userInfo);
  console.log(`  用户: ${userInfo.username} (${userInfo.email})`);
  console.log(`  邀请码: ${userInfo.invite_code}`);
  console.log(`  剩余邀请: ${userInfo.invites_remaining}`);
  console.log(`  帖子数: ${userInfo.post_count}`);
  
  sendToBackground({ type: 'USER_INFO', data: userInfo });
}

// 🆕 处理配额信息
function handleQuota(data) {
  console.log('📊 处理配额信息:', data);
  
  // 检查是否有 rate_limit_and_credit_balance 字段
  const rateLimit = data.rate_limit_and_credit_balance || data;
  
  // 🆕 获取当前账号信息（从之前捕获的用户信息中获取）
  const accountEmail = window.currentUserEmail || null;
  const userId = window.currentUserId || null;
  
  const quotaInfo = {
    type: 'QUOTA',
    // 🆕 添加账号信息
    account_email: accountEmail,
    user_id: userId,
    // 剩余视频数量
    estimated_num_videos_remaining: rateLimit.estimated_num_videos_remaining,
    estimated_num_purchased_videos_remaining: rateLimit.estimated_num_purchased_videos_remaining,
    credit_remaining: rateLimit.credit_remaining,
    // 速率限制
    rate_limit_reached: rateLimit.rate_limit_reached,
    access_resets_in_seconds: rateLimit.access_resets_in_seconds,
    type_status: rateLimit.type,
    // 兼容旧格式
    remaining: data.remaining || rateLimit.estimated_num_videos_remaining,
    total: data.total,
    used: data.used,
    reset_at: data.reset_at,
    captured_at: new Date().toISOString()
  };
  
  console.log('✅ 配额信息已提取:', quotaInfo);
  console.log(`  账号: ${accountEmail || '未知'}`);
  console.log(`  剩余视频数: ${quotaInfo.estimated_num_videos_remaining}`);
  console.log(`  剩余积分: ${quotaInfo.credit_remaining}`);
  console.log(`  速率限制: ${quotaInfo.rate_limit_reached ? '已达到' : '未达到'}`);
  
  sendToBackground({ type: 'QUOTA', data: quotaInfo });
}

// 🆕 处理创建视频
function handleCreateVideo(data) {
  console.log('🎬 处理创建视频 - 原始数据:', JSON.stringify(data, null, 2));
  
  // 尝试多种方式提取task_id
  let task_id = data.id || data.task_id || data.taskId || data.task?.id;
  
  // 如果还是没有，尝试从嵌套对象中查找
  if (!task_id && typeof data === 'object') {
    // 遍历所有属性查找可能的task_id
    for (const key in data) {
      if (key.toLowerCase().includes('task') && data[key]) {
        if (typeof data[key] === 'string' && data[key].startsWith('task_')) {
          task_id = data[key];
          console.log(`  ✓ 从 ${key} 中找到 task_id: ${task_id}`);
          break;
        } else if (typeof data[key] === 'object' && data[key].id) {
          task_id = data[key].id;
          console.log(`  ✓ 从 ${key}.id 中找到 task_id: ${task_id}`);
          break;
        }
      }
    }
  }
  
  const createInfo = {
    type: 'CREATE_VIDEO',
    task_id: task_id,
    generation_id: data.generation_id || data.generationId,
    prompt: data.prompt || data.text,
    status: data.status,
    task_type: data.task_type || data.taskType,
    priority: data.priority,
    draft: data.draft,
    created_at: data.created_at || data.createdAt || new Date().toISOString(),
    captured_at: new Date().toISOString(),
    raw_data: data  // 保存原始数据用于调试
  };
  
  console.log('✅ 创建视频信息已提取:', createInfo);
  console.log(`  任务 ID: ${createInfo.task_id || '(未找到)'}`);
  console.log(`  任务类型: ${createInfo.task_type || '(未知)'}`);
  console.log(`  优先级: ${createInfo.priority || '(未知)'}`);
  
  if (!createInfo.task_id) {
    console.warn('⚠️ 警告: 未能提取 task_id，数据可能不完整');
    console.warn('  原始数据键:', Object.keys(data));
  }
  
  sendToBackground({ type: 'CREATE_VIDEO', data: createInfo });
}

// 🆕 处理视频进度
function handleVideoProgress(data) {
  console.log('📈 处理视频进度:', data);
  
  // 可能是数组或单个对象
  const tasks = Array.isArray(data) ? data : [data];
  
  console.log(`📊 共 ${tasks.length} 个任务`);
  
  tasks.forEach(task => {
    if (task && task.id) {
      const progressInfo = {
        type: 'VIDEO_PROGRESS',
        task_id: task.id,
        task_type: task.task_type,
        status: task.status,
        progress_pct: task.progress_pct,
        prompt: task.prompt,
        title: task.title,
        thumbnail_url: task.thumbnail_url,
        failure_reason: task.failure_reason,
        generations: task.generations,
        captured_at: new Date().toISOString()
      };
      
      console.log(`✅ 视频进度已提取 [${task.id}]:`, progressInfo);
      console.log(`  状态: ${task.status}`);
      console.log(`  进度: ${task.progress_pct}%`);
      console.log(`  提示词: ${task.prompt}`);
      
      sendToBackground({ type: 'VIDEO_PROGRESS', data: progressInfo });
    }
  });
}

// 🆕 处理视频详情
function handleVideoDetail(data) {
  console.log('🎥 处理视频详情:', data);
  
  if (isValidVideoData(data)) {
    if (isCurrentUserVideo(data)) {
      console.log('✅ 发现有效的视频数据（当前用户）');
      console.log('  - Post ID:', data.post.id);
      console.log('  - Text:', data.post.text);
      console.log('  - Video URL:', data.post.attachments[0].url);
      sendToBackground(data);
    }
  }
}

// 🆕 处理草稿列表
function handleDraftsList(data) {
  console.log('📝 处理草稿列表:', data);
  
  if (!data.items || !Array.isArray(data.items)) {
    console.log('⚠️ 草稿列表格式不正确');
    return;
  }
  
  console.log(`📊 共 ${data.items.length} 个草稿`);
  
  let successCount = 0;
  let violationCount = 0;
  let otherCount = 0;
  
  const unpublishedDrafts = []; // 🆕 收集未发布的草稿
  
  data.items.forEach((item, index) => {
    if (!item || !item.id) {
      console.log(`⚠️ 草稿 [${index}] 缺少 ID，跳过`);
      return;
    }
    
    const draftInfo = {
      type: 'DRAFT',
      // 基本信息
      id: item.id,
      generation_id: item.generation_id,
      kind: item.kind,
      task_id: item.task_id,
      
      // 提示词和标题
      prompt: item.prompt,
      title: item.title,
      
      // 状态
      draft_reviewed: item.draft_reviewed,
      
      // 视频信息
      width: item.width,
      height: item.height,
      generation_type: item.generation_type,
      
      // URL（根据 kind 类型选择）
      url: null,
      downloadable_url: null,
      thumbnail_url: null,
      
      // 违规信息（如果是 content_violation）
      reason: item.reason,
      reason_str: item.reason_str,
      markdown_reason_str: item.markdown_reason_str,
      
      // 时间戳
      created_at: item.created_at,
      captured_at: new Date().toISOString()
    };
    
    // 根据 kind 类型处理
    if (item.kind === 'sora_draft') {
      // 正常草稿
      draftInfo.url = item.url;
      draftInfo.downloadable_url = item.downloadable_url;
      
      // 提取缩略图
      if (item.encodings && item.encodings.thumbnail) {
        draftInfo.thumbnail_url = item.encodings.thumbnail.url;
      }
      
      successCount++;
      console.log(`✅ 草稿 [${index + 1}/${data.items.length}] - 成功`);
      console.log(`  ID: ${draftInfo.id}`);
      console.log(`  任务ID: ${draftInfo.task_id}`);
      console.log(`  提示词: ${draftInfo.prompt}`);
      console.log(`  已审核: ${draftInfo.draft_reviewed}`);
      
      // 🆕 只添加未审核的草稿到发布列表（draft_reviewed === false 表示未发布）
      if (draftInfo.draft_reviewed === false) {
        unpublishedDrafts.push({
          draft_id: item.id,
          generation_id: item.generation_id,
          task_id: item.task_id,
          prompt: item.prompt,
          draft_url: `https://sora.chatgpt.com/d/${item.generation_id || item.id}`,
          thumbnail_url: draftInfo.thumbnail_url
        });
        console.log(`  📤 添加到未发布列表`);
      } else {
        console.log(`  ✓ 已发布，跳过`);
      }
      
    } else if (item.kind === 'sora_content_violation') {
      // 内容违规
      violationCount++;
      console.log(`⚠️ 草稿 [${index + 1}/${data.items.length}] - 内容违规`);
      console.log(`  ID: ${draftInfo.id}`);
      console.log(`  任务ID: ${draftInfo.task_id}`);
      console.log(`  提示词: ${draftInfo.prompt}`);
      console.log(`  违规原因: ${draftInfo.reason_str}`);
      
    } else {
      // 其他类型
      otherCount++;
      console.log(`ℹ️ 草稿 [${index + 1}/${data.items.length}] - 其他类型: ${item.kind}`);
    }
    
    // 发送到后台
    sendToBackground({ type: 'DRAFT', data: draftInfo });
  });
  
  console.log(`📊 草稿列表处理完成:`);
  console.log(`  ✅ 成功: ${successCount}`);
  console.log(`  ⚠️ 违规: ${violationCount}`);
  console.log(`  ℹ️ 其他: ${otherCount}`);
  console.log(`  📝 总计: ${data.items.length}`);
  
  // 🆕 如果有未发布的草稿，通知 plug-in 插件
  if (unpublishedDrafts.length > 0) {
    console.log(`\n📤 发送 ${unpublishedDrafts.length} 个未发布草稿到 plug-in 插件...`);
    notifyPluginForPublish(unpublishedDrafts);
  }
}


// 🆕 通知 plug-in 插件进行发布
async function notifyPluginForPublish(unpublishedDrafts) {
  try {
    console.log(`\n📤 发送 ${unpublishedDrafts.length} 个未发布草稿到后端...`);
    
    // 方法 1: 通过 background script 发送到后端 API（绕过 CORS 限制）
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'SEND_TO_BACKEND',
        endpoint: '/api/drafts/queue',
        method: 'POST',
        data: {
          drafts: unpublishedDrafts,
          timestamp: new Date().toISOString()
        }
      });
      
      if (response && response.success) {
        console.log(`✅ 已发送到后端: ${response.result?.message || '成功'}`);
      } else {
        console.warn(`⚠️ 后端响应失败: ${response?.error || '未知错误'}`);
      }
    } catch (error) {
      console.warn(`⚠️ 无法连接后端: ${error.message}`);
    }
    
    // 方法 2: 同时保存到 Chrome Storage（作为备份）
    await chrome.storage.local.set({
      unpublishedDrafts: unpublishedDrafts,
      lastUpdate: new Date().toISOString()
    });
    
    console.log(`✅ 已保存 ${unpublishedDrafts.length} 个未发布草稿到 Chrome Storage（备份）`);
    
  } catch (error) {
    console.error('❌ 保存未发布草稿失败:', error);
  }
}

// 🆕 处理已发布视频列表
function handlePublishedList(data) {
  console.log('📺 处理已发布视频列表:', data);
  
  if (!data.items || !Array.isArray(data.items)) {
    console.log('⚠️ 已发布视频列表格式不正确');
    return;
  }
  
  console.log(`📊 共 ${data.items.length} 个已发布视频`);
  
  let successCount = 0;
  
  data.items.forEach((item, index) => {
    if (!item || !item.post) {
      console.log(`⚠️ 视频 [${index}] 缺少 post 数据，跳过`);
      return;
    }
    
    const post = item.post;
    
    // 只处理当前用户的视频
    if (!post.is_owner) {
      console.log(`⏭️ 跳过非当前用户的视频: ${post.id}`);
      return;
    }
    
    const publishedInfo = {
      type: 'PUBLISHED_VIDEO',
      // 基本信息
      post_id: post.id,
      permalink: post.permalink,
      
      // 文本和标签
      text: post.text,
      discovery_phrase: post.discovery_phrase,
      emoji: post.emoji,
      
      // 🆕 从附件中提取 generation_id 和 task_id
      generation_id: post.attachments?.[0]?.generation_id,
      task_id: post.attachments?.[0]?.task_id,
      
      // 附件信息
      attachments: post.attachments,
      
      // 统计信息
      like_count: post.like_count,
      dislike_count: post.dislike_count,
      view_count: post.view_count,
      unique_view_count: post.unique_view_count,
      reply_count: post.reply_count,
      remix_count: post.remix_count,
      
      // 权限和可见性
      permissions: post.permissions,
      post_locations: post.post_locations,
      posted_to_public: post.posted_to_public,
      
      // 时间戳
      posted_at: post.posted_at,
      updated_at: post.updated_at,
      captured_at: new Date().toISOString()
    };
    
    successCount++;
    console.log(`✅ 已发布视频 [${index + 1}/${data.items.length}]`);
    console.log(`  Post ID: ${publishedInfo.post_id}`);
    console.log(`  Permalink: ${publishedInfo.permalink}`);
    console.log(`  Generation ID: ${publishedInfo.generation_id || '(无)'}`);
    console.log(`  Task ID: ${publishedInfo.task_id || '(无)'}`);
    console.log(`  文本: ${publishedInfo.text || '(无)'}`);
    console.log(`  发现短语: ${publishedInfo.discovery_phrase || '(无)'}`);
    console.log(`  观看次数: ${publishedInfo.view_count}`);
    
    // 发送到后台
    sendToBackground({ type: 'PUBLISHED_VIDEO', data: publishedInfo });
  });
  
  console.log(`📊 已发布视频列表处理完成:`);
  console.log(`  ✅ 成功: ${successCount}`);
  console.log(`  📝 总计: ${data.items.length}`);
}

// 验证是否为有效的视频数据（不打印日志，只验证格式）
function isValidVideoData(data) {
  // 检查是否有 post 和 attachments
  const hasPost = data && data.post;
  const hasAttachments = hasPost && data.post.attachments && data.post.attachments.length > 0;
  const hasSoraVideo = hasAttachments && data.post.attachments[0].kind === 'sora';
  
  return hasSoraVideo;
}

// 检查视频是否属于当前用户
function isCurrentUserVideo(data) {
  const videoUserId = data.profile?.user_id;
  
  if (!currentUserId) {
    console.log('⚠️ 当前用户 ID 未知，无法过滤视频');
    return false; // 如果不知道当前用户，不保存任何视频
  }
  
  if (videoUserId === currentUserId) {
    return true;
  }
  
  console.log(`⏭️ 跳过其他用户的视频 (user_id: ${videoUserId})`);
  return false;
}

// 发送到后台脚本
function sendToBackground(data) {
  console.log('📤 准备发送数据到后台脚本...');
  
  chrome.runtime.sendMessage(
    { type: 'VIDEO_DATA', data },
    (response) => {
      if (chrome.runtime.lastError) {
        console.error('❌ 发送失败:', chrome.runtime.lastError);
      } else {
        console.log('✅ 发送成功:', response);
      }
    }
  );
}

// 监听页面上的视频元素
if (document.body) {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) { // Element node
          // 查找视频相关的元素
          const videoElements = node.querySelectorAll('video, [data-testid*="video"]');
          if (videoElements.length > 0) {
            console.log('检测到视频元素:', videoElements.length);
          }
        }
      });
    });
  });

  // 开始观察
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
} else {
  // 等待 body 加载
  document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            const videoElements = node.querySelectorAll('video, [data-testid*="video"]');
            if (videoElements.length > 0) {
              console.log('检测到视频元素:', videoElements.length);
            }
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}

// 页面加载完成后的初始化
window.addEventListener('load', () => {
  console.log('页面加载完成，Sora 视频抓包助手已就绪');
});


// ==================== 视频发布功能 ====================

// 监听来自页面的发布请求
window.addEventListener('message', async (event) => {
  // 只处理来自同源的消息
  if (event.source !== window) return;
  
  if (event.data.type === 'PUBLISH_VIDEO') {
    await publishVideoToSora(event.data.data);
  }
});

/**
 * 发布视频到 Sora
 * @param {Object} publishData - 发布数据
 * @param {number} publishData.task_id - 任务 ID
 * @param {string} publishData.sora_task_id - Sora 任务 ID (task_xxx)
 * @param {string} publishData.prompt - 提示词
 * @param {string} publishData.text - 发布文本
 */
async function publishVideoToSora(publishData) {
  console.log('\n' + '='.repeat(80));
  console.log('🚀 开始发布视频到 Sora');
  console.log('='.repeat(80));
  console.log('  任务 ID:', publishData.task_id);
  console.log('  Sora 任务 ID:', publishData.sora_task_id);
  console.log('  提示词:', publishData.prompt);
  
  try {
    // 步骤 1: 从 drafts API 获取 generation_id
    console.log('\n📡 步骤 1: 获取 generation_id...');
    const draftsResponse = await fetch('https://sora.chatgpt.com/backend/project_y/profile/drafts?limit=50', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      }
    });
    
    if (!draftsResponse.ok) {
      throw new Error(`获取草稿列表失败: HTTP ${draftsResponse.status}`);
    }
    
    const draftsData = await draftsResponse.json();
    console.log(`  找到 ${draftsData.items.length} 个草稿`);
    
    // 查找匹配的 draft
    const draft = draftsData.items.find(item => 
      item.task_id === publishData.sora_task_id && item.kind === 'sora_draft'
    );
    
    if (!draft) {
      console.error('❌ 未找到对应的草稿');
      console.log('  查找条件: task_id =', publishData.sora_task_id);
      console.log('  可用的草稿:');
      draftsData.items.forEach((item, index) => {
        console.log(`    [${index}] task_id: ${item.task_id}, kind: ${item.kind}`);
      });
      throw new Error('未找到对应的视频草稿，可能已被删除或发布');
    }
    
    const generation_id = draft.generation_id || draft.id;
    console.log('  ✅ 找到草稿');
    console.log('  Generation ID:', generation_id);
    console.log('  草稿类型:', draft.kind);
    
    // 步骤 2: 调用 Sora 发布 API
    console.log('\n📤 步骤 2: 发布视频...');
    
    const publishPayload = {
      generation_id: generation_id,
      text: publishData.text || publishData.prompt,
      post_locations: ['public'],
      share_setting: 'public'
    };
    
    console.log('  发布参数:', JSON.stringify(publishPayload, null, 2));
    
    const publishResponse = await fetch('https://sora.chatgpt.com/backend/project_y/post', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(publishPayload)
    });
    
    if (!publishResponse.ok) {
      const errorText = await publishResponse.text();
      console.error('  发布失败响应:', errorText);
      throw new Error(`发布失败: HTTP ${publishResponse.status} - ${errorText}`);
    }
    
    const publishResult = await publishResponse.json();
    console.log('  ✅ 发布成功！');
    console.log('  Post ID:', publishResult.post.id);
    console.log('  链接:', publishResult.post.permalink);
    console.log('  发布时间:', new Date(publishResult.post.posted_at * 1000).toLocaleString());
    
    // 步骤 3: 通知后端发布成功
    console.log('\n📡 步骤 3: 通知后端...');
    
    try {
      const callbackResponse = await fetch('http://localhost:8000/api/tasks/publish-callback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: publishData.task_id,
          post_id: publishResult.post.id,
          permalink: publishResult.post.permalink,
          posted_at: new Date(publishResult.post.posted_at * 1000).toISOString()
        })
      });
      
      if (callbackResponse.ok) {
        console.log('  ✅ 后端已更新');
      } else {
        console.warn('  ⚠️ 后端更新失败，但视频已发布');
      }
    } catch (error) {
      console.warn('  ⚠️ 无法连接后端，但视频已发布:', error.message);
    }
    
    console.log('\n' + '='.repeat(80));
    console.log('✅ 视频发布完成！');
    console.log('='.repeat(80));
    
    // 通知页面发布成功
    window.postMessage({
      type: 'PUBLISH_VIDEO_SUCCESS',
      data: {
        task_id: publishData.task_id,
        post_id: publishResult.post.id,
        permalink: publishResult.post.permalink
      }
    }, '*');
    
    alert(`✅ 视频发布成功！\n\n链接: ${publishResult.post.permalink}`);
    
  } catch (error) {
    console.error('\n' + '='.repeat(80));
    console.error('❌ 发布失败');
    console.error('='.repeat(80));
    console.error('  错误:', error);
    console.error('  堆栈:', error.stack);
    
    // 通知页面发布失败
    window.postMessage({
      type: 'PUBLISH_VIDEO_ERROR',
      data: {
        task_id: publishData.task_id,
        error: error.message
      }
    }, '*');
    
    alert(`❌ 视频发布失败\n\n错误: ${error.message}`);
  }
}

console.log('✅ 视频发布功能已加载');


