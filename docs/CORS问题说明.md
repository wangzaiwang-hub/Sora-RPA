# CORS 问题说明

## 问题描述

Chrome 浏览器窗口无法从 `https://sora.chatgpt.com` 直接访问本地后端（localhost:8000），报错：
```
Access to fetch at 'http://localhost:8000/api/drafts/queue' from origin 'https://sora.chatgpt.com' 
has been blocked by CORS policy: Permission was denied for this request to access the `unknown` address space.
```

## 原因

Chrome 142+ 版本引入了新的安全策略 "Private Network Access"，默认阻止从公网（https）访问本地网络（localhost）。

## 解决方案 ✅

**已通过 Chrome 扩展的 background script 代理请求解决**

### 实现原理

1. Content script（运行在网页上下文）不直接访问 localhost
2. Content script 发送消息给 background script
3. Background script（不受 Private Network Access 限制）执行实际的 fetch 请求
4. Background script 返回结果给 content script

### 修改内容

1. **plug-renwu/content.js**
   - 将直接的 `fetch('http://localhost:8000/...')` 改为 `chrome.runtime.sendMessage()`
   - 通过消息传递请求参数（endpoint, method, data）

2. **plug-renwu/background.js**
   - 新增 `SEND_TO_BACKEND` 消息类型处理
   - 新增 `handleBackendRequest()` 函数作为请求代理
   - 支持所有 HTTP 方法（GET, POST, PUT, DELETE 等）

### 使用方法

Content script 中发送请求：
```javascript
const response = await chrome.runtime.sendMessage({
  type: 'SEND_TO_BACKEND',
  endpoint: '/api/drafts/queue',
  method: 'POST',
  data: { /* 请求数据 */ }
});

if (response && response.success) {
  console.log('成功:', response.result);
} else {
  console.error('失败:', response.error);
}
```

## 其他可能的方案（未采用）

### 方案1：只使用特定窗口
在前端"窗口管理"页面，只打开和使用能正常访问的窗口。

### 方案2：降级 Chrome 版本
将窗口的 Chrome 版本改为 141 或更早版本。

### 方案3：添加启动参数
为浏览器添加启动参数（需要 ixbrowser 支持）：
```
--disable-features=BlockInsecurePrivateNetworkRequests
```

### 方案4：使用代理（复杂）
将后端部署到公网服务器，使用 HTTPS 访问。

## 总结

通过 Chrome 扩展的 background script 代理，完美解决了 CORS 和 Private Network Access 的限制，无需修改浏览器配置或降级版本。
