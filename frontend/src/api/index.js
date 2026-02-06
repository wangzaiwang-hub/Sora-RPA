import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 创建另一个实例用于 /v1 接口
const publicApi = axios.create({
  baseURL: '/v1',
  timeout: 30000
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

publicApi.interceptors.response.use(
  response => response.data,
  error => {
    console.error('Public API Error:', error)
    return Promise.reject(error)
  }
)

export default {
  // 统计信息
  getStats() {
    return api.get('/stats')
  },
  
  // 视频统计（来自插件）
  getVideoStats() {
    return publicApi.get('/videos/stats')
  },
  
  // 账号管理
  getAccounts() {
    return api.get('/accounts')
  },
  
  importAccounts(accounts) {
    return api.post('/accounts/import', accounts)
  },
  
  deleteAccount(id) {
    return api.delete(`/accounts/${id}`)
  },
  
  // 任务管理
  getTasks(accountId = null) {
    return api.get('/tasks', { params: { account_id: accountId } })
  },
  
  importTasks(tasks) {
    return api.post('/tasks/import', tasks)
  },
  
  importTasksFromFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/tasks/import/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  executeTask(taskId) {
    return api.post(`/tasks/${taskId}/execute`)
  },
  
  deleteTask(taskId) {
    return api.delete(`/tasks/${taskId}`)
  },
  
  retryTask(taskId) {
    return api.post(`/tasks/${taskId}/retry`)
  },
  
  terminateTask(taskId) {
    return api.post(`/tasks/${taskId}/terminate`)
  },
  
  batchDeleteTasks(taskIds) {
    return api.post('/tasks/batch-delete', taskIds)
  },
  
  batchRetryTasks(taskIds) {
    return api.post('/tasks/batch-retry', taskIds)
  },
  
  // 窗口管理
  controlWindows(profileIds, action) {
    return api.post('/windows/control', { profile_ids: profileIds, action })
  },
  
  getWindowsStatus() {
    return api.get('/windows/status')
  },
  
  getWindowStatus(profileId) {
    return api.get(`/windows/${profileId}/status`)
  },
  
  // 系统配置
  getConfig() {
    return api.get('/config')
  },
  
  updateConfig(config) {
    return api.post('/config', config)
  },
  
  // 视频管理
  deleteVideo(videoId) {
    return publicApi.post(`/videos/${videoId}/delete`)
  },
  
  batchDeleteVideos(videoIds) {
    return publicApi.post('/videos/batch-delete', videoIds)
  }
}
