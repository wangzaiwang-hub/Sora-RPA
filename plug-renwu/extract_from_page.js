// 从页面中直接提取视频数据
// 在视频详情页的控制台运行此脚本

console.log('%c🔍 开始从页面提取视频数据', 'color: #667eea; font-size: 16px; font-weight: bold;');

// 方法 1: 从 window 对象中查找
function findDataInWindow() {
  console.log('📦 方法 1: 搜索 window 对象...');
  
  const videoId = window.location.pathname.match(/\/p\/(s_[a-f0-9]+)/)?.[1];
  console.log('🎯 视频 ID:', videoId);
  
  // 搜索所有可能包含数据的属性
  const possibleKeys = Object.keys(window).filter(key => 
    key.includes('__NEXT') || 
    key.includes('__INITIAL') || 
    key.includes('data') ||
    key.includes('state') ||
    key.includes('props')
  );
  
  console.log('🔑 找到可能的数据键:', possibleKeys);
  
  for (const key of possibleKeys) {
    try {
      const value = window[key];
      const str = JSON.stringify(value);
      
      if (str.includes(videoId)) {
        console.log(`%c✅ 在 window.${key} 中找到视频数据!`, 'color: #10b981; font-weight: bold;');
        console.log('数据:', value);
        return value;
      }
    } catch (e) {
      // 跳过无法序列化的对象
    }
  }
  
  return null;
}

// 方法 2: 从 script 标签中查找
function findDataInScripts() {
  console.log('📦 方法 2: 搜索 script 标签...');
  
  const videoId = window.location.pathname.match(/\/p\/(s_[a-f0-9]+)/)?.[1];
  const scripts = document.querySelectorAll('script');
  
  console.log(`🔍 找到 ${scripts.length} 个 script 标签`);
  
  for (const script of scripts) {
    const content = script.textContent || script.innerHTML;
    
    if (content.includes(videoId) && content.includes('post')) {
      console.log('%c✅ 在 script 标签中找到视频数据!', 'color: #10b981; font-weight: bold;');
      
      // 尝试提取 JSON
      try {
        // 查找 JSON 对象
        const jsonMatch = content.match(/\{[^]*"post"[^]*\}/);
        if (jsonMatch) {
          const data = JSON.parse(jsonMatch[0]);
          console.log('提取的数据:', data);
          return data;
        }
      } catch (e) {
        console.log('⚠️ JSON 解析失败，尝试其他方法');
      }
      
      console.log('Script 内容片段:', content.substring(0, 500));
    }
  }
  
  return null;
}

// 方法 3: 使用 Performance API 查找请求
function findDataInPerformance() {
  console.log('📦 方法 3: 搜索 Performance API...');
  
  const videoId = window.location.pathname.match(/\/p\/(s_[a-f0-9]+)/)?.[1];
  const resources = performance.getEntriesByType('resource');
  
  const matchedResources = resources.filter(r => 
    r.name.includes(videoId) || r.name.includes('backend/project_y/post')
  );
  
  console.log(`🔍 找到 ${matchedResources.length} 个匹配的资源`);
  
  matchedResources.forEach(r => {
    console.log('资源 URL:', r.name);
    console.log('类型:', r.initiatorType);
    console.log('大小:', r.transferSize);
  });
  
  if (matchedResources.length > 0) {
    console.log('%c💡 找到请求 URL，但无法直接获取响应数据', 'color: #f59e0b;');
    console.log('💡 请在 Network 标签中查找这个 URL 并复制响应');
    return matchedResources[0].name;
  }
  
  return null;
}

// 方法 4: 手动从 Network 复制
function manualExtract() {
  console.log('📦 方法 4: 手动提取指南');
  console.log('');
  console.log('%c请按以下步骤操作:', 'color: #667eea; font-weight: bold;');
  console.log('1. 打开 Network 标签');
  console.log('2. 刷新页面 (Ctrl+R)');
  console.log('3. 搜索: backend/project_y/post');
  console.log('4. 点击该请求');
  console.log('5. 切换到 Response 标签');
  console.log('6. 右键 → Copy response');
  console.log('7. 运行: extractHelpers.sendManualData(粘贴的数据)');
}

// 执行所有方法
console.log('\n' + '='.repeat(80));
const windowData = findDataInWindow();
console.log('\n' + '='.repeat(80));
const scriptData = findDataInScripts();
console.log('\n' + '='.repeat(80));
const perfData = findDataInPerformance();
console.log('\n' + '='.repeat(80));

// 辅助函数
window.extractHelpers = {
  // 发送手动复制的数据
  sendManualData: (responseData) => {
    console.log('📤 处理手动数据...');
    
    const post = responseData.post || {};
    const profile = responseData.profile || {};
    const attachment = post.attachments?.[0] || {};
    
    const videoInfo = {
      post_id: post.id,
      text: post.text,
      caption: post.caption,
      posted_at: post.posted_at,
      updated_at: post.updated_at,
      permalink: post.permalink,
      share_ref: post.share_ref,
      like_count: post.like_count,
      view_count: post.view_count,
      unique_view_count: post.unique_view_count,
      remix_count: post.remix_count,
      reply_count: post.reply_count,
      user_id: profile.user_id,
      username: profile.username,
      profile_picture_url: profile.profile_picture_url,
      verified: profile.verified,
      generation_id: attachment.generation_id,
      task_id: attachment.task_id,
      video_url: attachment.url,
      downloadable_url: attachment.downloadable_url,
      download_url_watermark: attachment.download_urls?.watermark,
      download_url_no_watermark: attachment.download_urls?.no_watermark,
      width: attachment.width,
      height: attachment.height,
      n_frames: attachment.n_frames,
      prompt: attachment.prompt || post.text,
      source_url: attachment.encodings?.source?.path,
      source_size: attachment.encodings?.source?.size,
      thumbnail_url: attachment.encodings?.thumbnail?.path,
      md_url: attachment.encodings?.md?.path,
      ld_url: attachment.encodings?.ld?.path,
      gif_url: attachment.encodings?.gif?.path,
      emoji: post.emoji,
      discovery_phrase: post.discovery_phrase,
      source: post.source,
      captured_at: new Date().toISOString()
    };
    
    console.log('✅ 视频信息已提取:', videoInfo);
    
    // 发送到插件
    chrome.runtime.sendMessage(
      { type: 'VIDEO_DATA', data: responseData },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error('❌ 发送到插件失败:', chrome.runtime.lastError);
          console.log('💡 尝试直接发送到后端...');
          
          // 直接发送到后端
          fetch('http://localhost:8000/api/videos/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(videoInfo)
          })
          .then(r => r.json())
          .then(result => {
            console.log('✅ 直接发送到后端成功:', result);
          })
          .catch(error => {
            console.error('❌ 发送到后端失败:', error);
          });
        } else {
          console.log('✅ 发送到插件成功:', response);
        }
      }
    );
  },
  
  // 显示帮助
  help: () => {
    console.log(`
%c📖 使用说明

如果自动提取失败，请手动操作:

1. 打开 Network 标签
2. 刷新页面 (Ctrl+R)
3. 搜索: backend/project_y/post
4. 点击该请求 → Response 标签
5. 右键 → Copy response
6. 在控制台运行:

   const data = /* 粘贴复制的 JSON */;
   extractHelpers.sendManualData(data);

示例:
   const data = {"post": {...}, "profile": {...}};
   extractHelpers.sendManualData(data);
    `, 'color: #667eea;');
  }
};

// 显示结果
console.log('\n' + '='.repeat(80));
console.log('%c📊 提取结果总结', 'color: #667eea; font-size: 14px; font-weight: bold;');
console.log('');

if (windowData) {
  console.log('✅ 从 window 对象中找到数据');
  console.log('💡 运行: extractHelpers.sendManualData(/* window 中的数据 */)');
} else {
  console.log('❌ 未在 window 对象中找到数据');
}

if (scriptData) {
  console.log('✅ 从 script 标签中找到数据');
  console.log('💡 运行: extractHelpers.sendManualData(/* script 中的数据 */)');
} else {
  console.log('❌ 未在 script 标签中找到数据');
}

if (perfData) {
  console.log('✅ 找到请求 URL:', perfData);
  console.log('💡 请在 Network 标签中查找并复制响应');
} else {
  console.log('❌ 未在 Performance API 中找到请求');
}

console.log('');
console.log('%c💡 如果都失败了，请运行: extractHelpers.help()', 'color: #f59e0b;');
console.log('='.repeat(80));
