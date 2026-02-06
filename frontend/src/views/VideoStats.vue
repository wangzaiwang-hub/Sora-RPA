<template>
  <div class="video-stats">
    <el-card class="header-card">
      <div class="header">
        <h2>视频统计</h2>
        <el-button @click="refreshStats" :loading="loading" type="primary">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total">
              <el-icon><VideoCamera /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalStats.totalVideos }}</div>
              <div class="stat-label">总视频数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon quota">
              <el-icon><Tickets /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalStats.quotaRemaining !== null ? totalStats.quotaRemaining : '-' }}</div>
              <div class="stat-label">剩余次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon unpublished">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalStats.unpublishedVideos }}</div>
              <div class="stat-label">未发布</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon published">
              <el-icon><Check /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalStats.publishedVideos }}</div>
              <div class="stat-label">已发布</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最后更新时间 -->
    <el-card v-if="stats.accounts && stats.accounts.length > 0" class="update-card">
      <div class="update-info">
        <el-icon><Clock /></el-icon>
        最后更新: {{ formatTime(stats.accounts[0].lastUpdate) }}
      </div>
    </el-card>

    <!-- 账号视频表格 -->
    <el-card class="table-card">
      <el-table 
        :data="tableData" 
        style="width: 100%" 
        border 
        height="100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="账号" min-width="20%">
          <template #default="scope">
            <div>{{ scope.row.email }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="剩余次数" min-width="20%" align="center">
          <template #default="scope">
            <div class="quota-cell">
              <el-tag v-if="scope.row.quotaRemaining !== null" :type="scope.row.quotaRemaining > 10 ? 'success' : scope.row.quotaRemaining > 5 ? 'warning' : 'danger'" size="large">
                {{ scope.row.quotaRemaining }}
              </el-tag>
              <span v-else class="empty-text">-</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="未发布" min-width="20%" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.unpublished.length > 0" type="warning" size="large">
              {{ scope.row.unpublished.length }} 条
            </el-tag>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="已发布" min-width="20%" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.published.length > 0" type="success" size="large">
              {{ scope.row.published.length }} 条
            </el-tag>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" min-width="20%" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" @click="showVideoDetails(scope.row)">更多</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 视频详情弹窗 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      :title="`${currentAccount.email} - 视频详情`"
      width="80%"
      top="5vh"
    >
      <el-tabs v-model="activeTab">
        <el-tab-pane label="未发布" name="unpublished">
          <div v-if="currentAccount.unpublished && currentAccount.unpublished.length > 0" class="video-detail-list">
            <div v-for="video in currentAccount.unpublished" :key="video.id" class="video-detail-item">
              <div class="video-detail-info">
                <div class="video-detail-url">
                  <el-link :href="video.url" target="_blank" type="warning">
                    {{ video.url }}
                  </el-link>
                </div>
                <div v-if="video.prompt" class="video-detail-prompt">
                  <span class="label">提示词：</span>{{ video.prompt }}
                </div>
              </div>
              <el-button size="small" type="danger" @click="deleteVideoFromDialog(video)" plain>删除</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无未发布视频" />
        </el-tab-pane>
        
        <el-tab-pane label="已发布" name="published">
          <div v-if="currentAccount.published && currentAccount.published.length > 0" class="video-detail-list">
            <div v-for="video in currentAccount.published" :key="video.id" class="video-detail-item">
              <div class="video-detail-info">
                <div class="video-detail-url">
                  <el-link :href="video.url" target="_blank" type="success">
                    {{ video.url }}
                  </el-link>
                </div>
                <div v-if="video.prompt" class="video-detail-prompt">
                  <span class="label">提示词：</span>{{ video.prompt }}
                </div>
              </div>
              <el-button size="small" type="danger" @click="deleteVideoFromDialog(video)" plain>删除</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无已发布视频" />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCamera, Check, Tickets, Clock, Refresh, User } from '@element-plus/icons-vue'
import api from '../api'

const loading = ref(false)
const stats = ref({
  accounts: []
})
const lastUpdateTime = ref(null)
const detailDialogVisible = ref(false)
const activeTab = ref('unpublished')
const currentAccount = ref({
  email: '',
  unpublished: [],
  published: []
})
const selectedAccounts = ref([])

// 计算总统计数据
const totalStats = computed(() => {
  if (!stats.value.accounts || stats.value.accounts.length === 0) {
    return {
      totalVideos: 0,
      quotaRemaining: 0,
      unpublishedVideos: 0,
      publishedVideos: 0
    }
  }
  
  return stats.value.accounts.reduce((acc, account) => {
    return {
      totalVideos: acc.totalVideos + account.totalVideos,
      quotaRemaining: acc.quotaRemaining + (account.quotaRemaining || 0), // 累加所有账号的配额
      unpublishedVideos: acc.unpublishedVideos + account.unpublishedVideos,
      publishedVideos: acc.publishedVideos + account.publishedVideos
    }
  }, {
    totalVideos: 0,
    quotaRemaining: 0,
    unpublishedVideos: 0,
    publishedVideos: 0
  })
})

// 表格数据
const tableData = computed(() => {
  if (!stats.value.accounts) return []
  
  return stats.value.accounts.map(account => ({
    name: account.account.name,
    email: account.account.email,
    image: account.account.image,
    quotaRemaining: account.quotaRemaining,
    generatingCount: account.generatingVideos,
    unpublishedCount: account.unpublishedVideos,
    publishedCount: account.publishedVideos,
    generating: account.videos.generating || [],
    unpublished: account.videos.unpublished || [],
    published: account.videos.published || []
  }))
})

const refreshStats = async () => {
  loading.value = true
  try {
    const res = await api.getVideoStats()
    if (res.success) {
      const newData = res.data
      
      // 检测数据是否有变化
      const hasChanges = JSON.stringify(stats.value) !== JSON.stringify(newData)
      
      if (hasChanges && lastUpdateTime.value) {
        // 数据有变化，显示通知
        ElMessage.success('数据已更新')
      }
      
      stats.value = newData
      lastUpdateTime.value = Date.now()
    }
  } catch (error) {
    ElMessage.error('获取数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const deleteVideo = async (video, accountEmail) => {
  try {
    // 构建确认消息，显示提示词
    let confirmMessage = '确定要删除这个视频吗？\n\n'
    confirmMessage += `URL: ${video.url}\n`
    if (video.prompt) {
      confirmMessage += `提示词: ${video.prompt}\n`
    }
    confirmMessage += `\n删除后提示词将被记录，方便以后对照。`
    
    await ElMessageBox.confirm(confirmMessage, '删除视频', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    })
    
    const res = await api.deleteVideo(video.id)
    if (res.success) {
      // 显示删除成功消息，包含提示词
      let successMsg = '视频已删除'
      if (res.data && res.data.prompt) {
        successMsg += `\n提示词: ${res.data.prompt}`
        console.log('[删除视频]', {
          video_id: res.data.video_id,
          url: res.data.url,
          prompt: res.data.prompt,
          status: res.data.status,
          account: res.data.account_email,
          deleted_at: new Date().toLocaleString('zh-CN')
        })
      }
      ElMessage.success(successMsg)
      refreshStats()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || error))
    }
  }
}

const showVideoDetails = (row) => {
  currentAccount.value = {
    email: row.email,
    unpublished: row.unpublished || [],
    published: row.published || []
  }
  activeTab.value = 'unpublished'
  detailDialogVisible.value = true
}

const handleSelectionChange = (selection) => {
  selectedAccounts.value = selection
  console.log('已选择账号:', selection.map(s => s.email))
}

const deleteVideoFromDialog = async (video) => {
  await deleteVideo(video, currentAccount.value.email)
  // 刷新后更新当前账号数据
  await refreshStats()
  // 更新弹窗中的数据
  const updatedAccount = tableData.value.find(acc => acc.email === currentAccount.value.email)
  if (updatedAccount) {
    currentAccount.value = {
      email: updatedAccount.email,
      unpublished: updatedAccount.unpublished || [],
      published: updatedAccount.published || []
    }
  }
}

const viewDetails = (row) => {
  ElMessage.info('查看详情功能开发中...')
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  refreshStats()
  // 每5秒自动刷新（更频繁的轮询以实现近实时更新）
  setInterval(refreshStats, 5000)
})
</script>

<style scoped>
.video-stats {
  padding: 20px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header-card {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  margin: 0;
  font-size: 24px;
}

.stats-row {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
}

.stat-icon.total {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.quota {
  background: linear-gradient(135deg, #ffa726 0%, #fb8c00 100%);
}

.stat-icon.published {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.generating {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.unpublished {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.update-card {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.update-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.table-card :deep(.el-table) {
  flex: 1;
  overflow: auto;
}

.account-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-info {
  flex: 1;
}

.account-name {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.account-email {
  font-size: 12px;
  color: #909399;
}

.account-cell-simple {
  padding: 4px 0;
}

.account-cell-simple .account-name {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.account-cell-simple .account-email {
  font-size: 12px;
  color: #909399;
}

.empty-text {
  color: #909399;
  text-align: center;
  padding: 8px 0;
}

/* 弹窗样式 */
.video-detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
  padding: 10px;
}

.video-detail-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
}

.video-detail-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.video-detail-info {
  flex: 1;
  min-width: 0;
}

.video-detail-url {
  margin-bottom: 8px;
  font-size: 14px;
  word-break: break-all;
}

.video-detail-prompt {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  padding: 8px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.video-detail-prompt .label {
  font-weight: bold;
  color: #303133;
  margin-right: 4px;
}

.video-detail-item .el-button {
  flex-shrink: 0;
  margin-top: 4px;
}
</style>
