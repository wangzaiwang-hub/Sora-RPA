<template>
  <div class="windows-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <span style="font-weight: bold; margin-right: 15px;">窗口管理</span>
            <el-tag type="warning">
              队列中任务: {{ unassignedTasks }} 个
            </el-tag>
          </div>
          <div>
            <el-select v-model="pageSize" size="small" style="width: 100px; margin-right: 10px;">
              <el-option :value="10" label="10条/页" />
              <el-option :value="20" label="20条/页" />
              <el-option :value="50" label="50条/页" />
            </el-select>
            <el-button type="success" @click="batchControl('open')">
              <el-icon><VideoPlay /></el-icon>
              批量打开
            </el-button>
            <el-button type="warning" @click="batchControl('close')">
              <el-icon><VideoPause /></el-icon>
              批量关闭
            </el-button>
            <el-button @click="loadStatus">
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="paginatedWindows" 
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="profile_id" label="窗口ID" width="100" />
        <el-table-column prop="name" label="窗口名称" width="150" />
        <el-table-column prop="username" label="关联账号" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.has_account" type="success">{{ row.username }}</el-tag>
            <el-tag v-else type="info">{{ row.username }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quota_remaining" label="剩余次数" width="120">
          <template #default="{ row }">
            <span v-if="row.quota_remaining !== null && row.quota_remaining !== undefined">
              <el-tag v-if="row.quota_remaining > 10" type="success">{{ row.quota_remaining }} 次</el-tag>
              <el-tag v-else-if="row.quota_remaining > 0" type="warning">{{ row.quota_remaining }} 次</el-tag>
              <el-tag v-else type="danger">{{ row.quota_remaining }} 次</el-tag>
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="work_status" label="工作状态" width="150">
          <template #default="{ row }">
            <div>
              <el-tag v-if="row.work_status === 'busy'" type="danger">执行中</el-tag>
              <el-tag v-else-if="row.work_status === 'idle'" type="success">空闲</el-tag>
              <el-tag v-else-if="row.work_status === 'error'" type="danger">异常</el-tag>
              <el-tag v-else type="info">未知</el-tag>
              <div v-if="row.work_status === 'error' && row.error_time" style="font-size: 12px; color: #909399; margin-top: 4px;">
                {{ formatErrorTime(row.error_time) }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="current_task_id" label="当前任务" width="100">
          <template #default="{ row }">
            {{ row.current_task_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="pending_tasks" label="待处理任务" width="120">
          <template #default="{ row }">
            <el-badge :value="row.pending_tasks" :hidden="row.pending_tasks === 0" type="warning">
              <span>{{ row.pending_tasks }} 个</span>
            </el-badge>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="窗口状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_open ? 'success' : 'info'">
              {{ row.is_open ? '已打开' : '未打开' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button 
              v-if="!row.is_open"
              size="small" 
              type="success"
              @click="openWindow(row.profile_id)"
            >
              打开
            </el-button>
            <el-button 
              v-else
              size="small" 
              type="warning"
              :loading="isClosing(row.profile_id)"
              :disabled="isClosing(row.profile_id)"
              @click="closeWindow(row.profile_id)"
            >
              {{ isClosing(row.profile_id) ? '关闭中...' : '关闭' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-footer">
        <el-pagination
          v-if="windows.length > pageSize"
          :current-page="currentPage"
          :page-size="pageSize"
          :total="windows.length"
          layout="total, prev, pager, next"
          @current-change="currentPage = $event"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const windows = ref([])
const selectedWindows = ref([])
const unassignedTasks = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const closingWindows = ref(new Set()) // 正在关闭的窗口ID集合

// 分页后的窗口数据
const paginatedWindows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return windows.value.slice(start, start + pageSize.value)
})

const loadStatus = async () => {
  try {
    const res = await api.getWindowsStatus()
    if (res.success) {
      windows.value = res.data
      unassignedTasks.value = res.unassigned_tasks || 0
    }
  } catch (error) {
    ElMessage.error('加载窗口状态失败')
  }
}

const handleSelectionChange = (selection) => {
  selectedWindows.value = selection.map(w => w.profile_id)
}

const openWindow = async (profileId) => {
  try {
    const res = await api.controlWindows([profileId], 'open')
    if (res.success) {
      ElMessage.success('窗口已打开')
      loadStatus()
    }
  } catch (error) {
    ElMessage.error('打开窗口失败')
  }
}

const closeWindow = async (profileId) => {
  // 防止重复点击
  if (closingWindows.value.has(profileId)) {
    return
  }
  
  closingWindows.value.add(profileId)
  
  try {
    const res = await api.controlWindows([profileId], 'close')
    if (res.success) {
      ElMessage.success('正在关闭窗口...')
      // 延迟2秒后刷新状态，给后台时间关闭窗口
      setTimeout(() => {
        loadStatus()
        closingWindows.value.delete(profileId)
      }, 2000)
    }
  } catch (error) {
    ElMessage.error('关闭窗口失败')
    closingWindows.value.delete(profileId)
  }
}

const batchControl = async (action) => {
  if (selectedWindows.value.length === 0) {
    ElMessage.warning('请先选择窗口')
    return
  }
  
  // 如果是关闭操作，防止重复点击
  if (action === 'close') {
    const hasClosing = selectedWindows.value.some(id => closingWindows.value.has(id))
    if (hasClosing) {
      return
    }
    selectedWindows.value.forEach(id => closingWindows.value.add(id))
  }
  
  try {
    const res = await api.controlWindows(selectedWindows.value, action)
    if (res.success) {
      ElMessage.success(`批量${action === 'open' ? '打开' : '关闭'}成功`)
      
      if (action === 'close') {
        // 延迟2秒后刷新状态
        setTimeout(() => {
          loadStatus()
          selectedWindows.value.forEach(id => closingWindows.value.delete(id))
        }, 2000)
      } else {
        loadStatus()
      }
    }
  } catch (error) {
    ElMessage.error(`批量${action === 'open' ? '打开' : '关闭'}失败`)
    if (action === 'close') {
      selectedWindows.value.forEach(id => closingWindows.value.delete(id))
    }
  }
}

const formatErrorTime = (timeStr) => {
  try {
    const date = new Date(timeStr)
    const now = new Date()
    const diff = Math.floor((now - date) / 1000) // 秒
    
    if (diff < 60) return `${diff}秒前`
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    return `${Math.floor(diff / 86400)}天前`
  } catch {
    return timeStr
  }
}

// 检查窗口是否正在关闭
const isClosing = (profileId) => {
  return closingWindows.value.has(profileId)
}

onMounted(() => {
  loadStatus()
  // 每10秒刷新一次
  setInterval(loadStatus, 10000)
})
</script>

<style scoped>
.windows-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
