// 自动发布脚本 - 在草稿页面中执行
(function() {
  console.log('🎬 自动发布脚本已加载');
  console.log('📍 当前 URL:', window.location.href);
  
  // 提取草稿 ID
  const draftIdMatch = window.location.href.match(/\/d\/(gen_[a-z0-9]+)/);
  const draftId = draftIdMatch ? draftIdMatch[1] : null;
  
  if (!draftId) {
    console.error('❌ 无法提取草稿 ID');
    notifyResult(false, null, null, '无法提取草稿 ID');
    return;
  }
  
  console.log(`📝 草稿 ID: ${draftId}`);
  
  // 等待页面完全加载
  if (document.readyState !== 'complete') {
    window.addEventListener('load', () => {
      setTimeout(startPublish, 2000);
    });
  } else {
    setTimeout(startPublish, 2000);
  }
  
  /**
   * 开始发布流程
   */
  async function startPublish() {
    console.log('\n' + '='.repeat(80));
    console.log('🚀 开始发布流程');
    console.log('='.repeat(80));
    
    try {
      // 步骤 1: 检查是否已经在编辑状态
      let textarea = document.querySelector('textarea[placeholder="Add caption..."]');
      
      if (!textarea) {
        // 步骤 2: 点击编辑按钮
        console.log('📝 步骤 1: 点击编辑按钮');
        await clickEditButton();
        await wait(2000);
      } else {
        console.log('✅ 已在编辑状态');
      }
      
      // 步骤 3: 清空提示词
      console.log('📝 步骤 2: 清空提示词');
      await clearPrompt();
      await wait(1000);
      
      // 步骤 4: 点击保存按钮
      console.log('📝 步骤 3: 点击保存按钮');
      await clickSaveButton();
      await wait(2000);
      
      // 步骤 5: 点击 Post 按钮
      console.log('📝 步骤 4: 点击 Post 按钮');
      await clickPostButton();
      
      // 步骤 6: 等待跳转到发布页面
      console.log('📝 步骤 5: 等待跳转到发布页面...');
      const publishedUrl = await waitForPublish();
      
      if (publishedUrl) {
        // 提取 post_id
        const postIdMatch = publishedUrl.match(/\/p\/(s_[a-f0-9]+)/);
        const postId = postIdMatch ? postIdMatch[1] : null;
        
        console.log('\n' + '='.repeat(80));
        console.log('✅ 发布成功！');
        console.log('='.repeat(80));
        console.log(`📍 草稿 URL: https://sora.chatgpt.com/d/${draftId}`);
        console.log(`📍 发布 URL: ${publishedUrl}`);
        console.log(`🆔 Post ID: ${postId}`);
        console.log('='.repeat(80));
        
        notifyResult(true, publishedUrl, postId, null);
      } else {
        throw new Error('未检测到跳转到发布页面');
      }
      
    } catch (error) {
      console.error('\n' + '='.repeat(80));
      console.error('❌ 发布失败');
      console.error('='.repeat(80));
      console.error('错误:', error.message);
      console.error('='.repeat(80));
      
      notifyResult(false, null, null, error.message);
    }
  }
  
  /**
   * 点击编辑按钮
   */
  async function clickEditButton() {
    const allButtons = document.querySelectorAll('button');
    const editButton = Array.from(allButtons).find(btn => {
      const svg = btn.querySelector('svg');
      const path = svg?.querySelector('path');
      const d = path?.getAttribute('d');
      return d && d.includes('M18.292 5.707');
    });
    
    if (!editButton) {
      throw new Error('未找到编辑按钮');
    }
    
    console.log('  ✅ 找到编辑按钮，点击...');
    editButton.click();
  }
  
  /**
   * 清空提示词
   */
  async function clearPrompt() {
    const textarea = document.querySelector('textarea[placeholder="Add caption..."]');
    if (!textarea) {
      throw new Error('未找到 textarea');
    }
    
    const originalPrompt = textarea.value;
    console.log(`  原始提示词: "${originalPrompt}"`);
    
    textarea.focus();
    textarea.value = '';
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
    
    console.log('  ✅ 提示词已清空');
  }
  
  /**
   * 点击保存按钮
   */
  async function clickSaveButton() {
    const allButtons = document.querySelectorAll('button');
    const saveButton = Array.from(allButtons).find(btn => {
      const svg = btn.querySelector('svg');
      const viewBox = svg?.getAttribute('viewBox');
      const path = svg?.querySelector('path');
      const d = path?.getAttribute('d');
      return viewBox === '0 0 18 19' && d && d.includes('M13.548 4.755');
    });
    
    if (!saveButton) {
      throw new Error('未找到保存按钮');
    }
    
    console.log('  ✅ 找到保存按钮，点击...');
    saveButton.setAttribute('data-disabled', 'false');
    saveButton.removeAttribute('disabled');
    saveButton.click();
  }
  
  /**
   * 点击 Post 按钮
   */
  async function clickPostButton() {
    const allButtons = document.querySelectorAll('button');
    const postButton = Array.from(allButtons).find(btn => 
      btn.textContent.trim() === 'Post' && 
      btn.classList.contains('bg-token-bg-inverse')
    );
    
    if (!postButton) {
      throw new Error('未找到 Post 按钮');
    }
    
    console.log('  ✅ 找到 Post 按钮，点击...');
    postButton.setAttribute('data-disabled', 'false');
    postButton.removeAttribute('disabled');
    postButton.click();
  }
  
  /**
   * 等待跳转到发布页面
   */
  async function waitForPublish() {
    return new Promise((resolve) => {
      let attempts = 0;
      const maxAttempts = 30; // 30秒超时
      
      const checkInterval = setInterval(() => {
        attempts++;
        const currentUrl = window.location.href;
        
        console.log(`  ⏳ 检查跳转... (${attempts}/${maxAttempts})`);
        
        if (currentUrl.includes('/p/s_')) {
          clearInterval(checkInterval);
          console.log('  ✅ 已跳转到发布页面');
          resolve(currentUrl);
        } else if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          console.log('  ❌ 等待跳转超时');
          resolve(null);
        }
      }, 1000);
    });
  }
  
  /**
   * 等待指定时间
   */
  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * 通知 background script 发布结果
   */
  function notifyResult(success, publishedUrl, postId, error) {
    chrome.runtime.sendMessage({
      type: 'PUBLISH_RESULT',
      success: success,
      published_url: publishedUrl,
      post_id: postId,
      error: error
    });
  }
  
})();
