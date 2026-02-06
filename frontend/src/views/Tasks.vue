<template>
  <div class="tasks-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div>
            <el-button type="primary" @click="showImportDialog = true">
              <el-icon><Plus /></el-icon>
              导入任务
            </el-button>
            <el-upload
              :show-file-list="false"
              :before-upload="handleFileUpload"
              accept=".json"
              style="display: inline-block; margin-left: 10px;"
            >
              <el-button type="success">
                <el-icon><Upload /></el-icon>
                上传文件
              </el-button>
            </el-upload>
          </div>
        </div>
      </template>
      
      <!-- 上半部分：待处理和进行中 -->
      <el-row :gutter="20" style="margin-bottom: 30px;">
        <el-col :span="12">
          <div class="section-header">
            <div class="section-title">待处理任务 ({{ pendingTasks.length }})</div>
            <el-select v-model="pendingPageSize" size="small" style="width: 100px;">
              <el-option :value="10" label="10条/页" />
              <el-option :value="20" label="20条/页" />
              <el-option :value="50" label="50条/页" />
            </el-select>
          </div>
          <el-table :data="paginatedPendingTasks" stripe max-height="400" @selection-change="handlePendingSelection">
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="系统ID" width="70" />
            <el-table-column prop="sora_task_id" label="Sora任务ID" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.sora_task_id" style="font-family: monospace; font-size: 12px;">{{ row.sora_task_id }}</span>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
            <el-table-column label="图片" width="100" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image"
                  :src="getProxyImageUrl(row.image)"
                  :preview-src-list="[getProxyImageUrl(row.image)]"
                  fit="cover"
                  style="width: 60px; height: 60px; border-radius: 4px; cursor: pointer;"
                  :preview-teleported="true"
                >
                  <template #error>
                    <div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; background: #f5f7fa; color: #909399; font-size: 12px;">
                      加载失败
                    </div>
                  </template>
                </el-image>
                <span v-else style="color: #C0C4CC;">-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="executeTask(row.id)">执行</el-button>
                <el-button size="small" type="danger" @click="deleteTask(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            <el-button v-if="pendingSelection.length > 0" size="small" type="danger" @click="batchDeleteTasks(pendingSelection)">
              批量删除 ({{ pendingSelection.length }})
            </el-button>
            <el-pagination
              v-if="pendingTasks.length > pendingPageSize"
              :current-page="pendingPage"
              :page-size="pendingPageSize"
              :total="pendingTasks.length"
              layout="total, prev, pager, next"
              @current-change="pendingPage = $event"
            />
          </div>
        </el-col>
        
        <el-col :span="12">
          <div class="section-header">
            <div class="section-title">进行中任务 ({{ runningTasks.length }})</div>
            <el-select v-model="runningPageSize" size="small" style="width: 100px;">
              <el-option :value="10" label="10条/页" />
              <el-option :value="20" label="20条/页" />
              <el-option :value="50" label="50条/页" />
            </el-select>
          </div>
          <el-table :data="paginatedRunningTasks" stripe max-height="400" @selection-change="handleRunningSelection">
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="系统ID" width="70" />
            <el-table-column prop="sora_task_id" label="Sora任务ID" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.sora_task_id" style="font-family: monospace; font-size: 12px;">{{ row.sora_task_id }}</span>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
            <el-table-column label="图片" width="100" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image"
                  :src="getProxyImageUrl(row.image)"
                  :preview-src-list="[getProxyImageUrl(row.image)]"
                  fit="cover"
                  style="width: 60px; height: 60px; border-radius: 4px; cursor: pointer;"
                  :preview-teleported="true"
                >
                  <template #error>
                    <div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; background: #f5f7fa; color: #909399; font-size: 12px;">
                      加载失败
                    </div>
                  </template>
                </el-image>
                <span v-else style="color: #C0C4CC;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" type="warning" @click="terminateTask(row.id)">终止</el-button>
                <el-button size="small" type="danger" @click="deleteTask(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            <el-button v-if="runningSelection.length > 0" size="small" type="warning" @click="batchTerminateTasks(runningSelection)" style="margin-right: 10px;">
              批量终止 ({{ runningSelection.length }})
            </el-button>
            <el-button v-if="runningSelection.length > 0" size="small" type="danger" @click="batchDeleteTasks(runningSelection)">
              批量删除 ({{ runningSelection.length }})
            </el-button>
            <el-pagination
              v-if="runningTasks.length > runningPageSize"
              :current-page="runningPage"
              :page-size="runningPageSize"
              :total="runningTasks.length"
              layout="total, prev, pager, next"
              @current-change="runningPage = $event"
            />
          </div>
        </el-col>
      </el-row>
      
      <el-divider />
      
      <!-- 下半部分：成功和失败 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="section-header">
            <div class="section-title">成功任务 ({{ successTasks.length }})</div>
            <el-select v-model="successPageSize" size="small" style="width: 100px;">
              <el-option :value="10" label="10条/页" />
              <el-option :value="20" label="20条/页" />
              <el-option :value="50" label="50条/页" />
            </el-select>
          </div>
          <el-table :data="paginatedSuccessTasks" stripe max-height="400" @selection-change="handleSuccessSelection">
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="系统ID" width="70" />
            <el-table-column prop="sora_task_id" label="Sora任务ID" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.sora_task_id" style="font-family: monospace; font-size: 12px;">{{ row.sora_task_id }}</span>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
            <el-table-column label="图片" width="100" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image"
                  :src="getProxyImageUrl(row.image)"
                  :preview-src-list="[getProxyImageUrl(row.image)]"
                  fit="cover"
                  style="width: 60px; height: 60px; border-radius: 4px; cursor: pointer;"
                  :preview-teleported="true"
                >
                  <template #error>
                    <div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; background: #f5f7fa; color: #909399; font-size: 12px;">
                      加载失败
                    </div>
                  </template>
                </el-image>
                <span v-else style="color: #C0C4CC;">-</span>
              </template>
            </el-table-column>
            <el-table-column label="发布状态" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.is_published" type="success" size="small">已发布</el-tag>
                <el-tag v-else type="info" size="small">未发布</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="end_time" label="完成时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <!-- 已发布：显示发布链接 -->
                <el-button v-if="row.is_published && row.permalink" size="small" type="success" @click="openVideo(row.permalink)">
                  查看
                </el-button>
                <!-- 未发布：显示草稿/视频链接 -->
                <el-button v-else-if="row.video_url" size="small" type="success" @click="openVideo(row.video_url)">
                  查看
                </el-button>
                <el-button size="small" type="danger" @click="deleteTask(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            <el-button v-if="successSelection.length > 0" size="small" type="danger" @click="batchDeleteTasks(successSelection)">
              批量删除 ({{ successSelection.length }})
            </el-button>
            <el-pagination
              v-if="successTasks.length > successPageSize"
              :current-page="successPage"
              :page-size="successPageSize"
              :total="successTasks.length"
              layout="total, prev, pager, next"
              @current-change="successPage = $event"
            />
          </div>
        </el-col>
        
        <el-col :span="12">
          <div class="section-header">
            <div class="section-title">失败任务 ({{ failedTasks.length }})</div>
            <el-select v-model="failedPageSize" size="small" style="width: 100px;">
              <el-option :value="10" label="10条/页" />
              <el-option :value="20" label="20条/页" />
              <el-option :value="50" label="50条/页" />
            </el-select>
          </div>
          <el-table :data="paginatedFailedTasks" stripe max-height="400" @selection-change="handleFailedSelection">
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="系统ID" width="70" />
            <el-table-column prop="sora_task_id" label="Sora任务ID" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.sora_task_id" style="font-family: monospace; font-size: 12px;">{{ row.sora_task_id }}</span>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
            <el-table-column label="图片" width="100" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image"
                  :src="getProxyImageUrl(row.image)"
                  :preview-src-list="[getProxyImageUrl(row.image)]"
                  fit="cover"
                  style="width: 60px; height: 60px; border-radius: 4px; cursor: pointer;"
                  :preview-teleported="true"
                >
                  <template #error>
                    <div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; background: #f5f7fa; color: #909399; font-size: 12px;">
                      加载失败
                    </div>
                  </template>
                </el-image>
                <span v-else style="color: #C0C4CC;">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误" show-overflow-tooltip width="150" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" type="warning" @click="retryTask(row.id)">重试</el-button>
                <el-button size="small" type="danger" @click="deleteTask(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            <el-button v-if="failedSelection.length > 0" size="small" type="warning" @click="batchRetryTasks(failedSelection)" style="margin-right: 10px;">
              批量重试 ({{ failedSelection.length }})
            </el-button>
            <el-button v-if="failedSelection.length > 0" size="small" type="danger" @click="batchDeleteTasks(failedSelection)">
              批量删除 ({{ failedSelection.length }})
            </el-button>
            <el-pagination
              v-if="failedTasks.length > failedPageSize"
              :current-page="failedPage"
              :page-size="failedPageSize"
              :total="failedTasks.length"
              layout="total, prev, pager, next"
              @current-change="failedPage = $event"
            />
          </div>
        </el-col>
      </el-row>
    </el-card>
    
    <!-- 导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入任务" width="600px">
      <el-form>
        <el-form-item label="选择账号">
          <el-select v-model="taskImport.account_id" placeholder="可选，不选则加入公共队列" clearable>
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.username"
              :value="account.id"
            />
          </el-select>
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            不选择账号时，任务会加入公共队列，由空闲窗口自动领取
          </div>
        </el-form-item>
        
        <el-form-item label="导入方式">
          <el-radio-group v-model="importMethod">
            <el-radio label="manual">手动输入</el-radio>
            <el-radio label="batch">批量导入</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <template v-if="importMethod === 'manual'">
          <el-form-item label="提示词">
            <el-input v-model="taskImport.prompt" type="textarea" :rows="4" placeholder="请输入提示词" />
          </el-form-item>
          <el-form-item label="图片URL">
            <el-input v-model="taskImport.image" placeholder="可选，输入图片URL" />
          </el-form-item>
        </template>
        
        <template v-else>
          <el-form-item label="批量数据">
            <el-input
              v-model="batchData"
              type="textarea"
              :rows="10"
              placeholder="格式：提示词|图片URL（每行一个任务，图片URL可选）&#10;示例：&#10;一只猫在跑步|&#10;美丽的日落|https://example.com/image.jpg"
            />
          </el-form-item>
        </template>
      </el-form>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importTasks">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const tasks = ref([])
const accounts = ref([])
const showImportDialog = ref(false)
const importMethod = ref('manual')
const taskImport = ref({ account_id: null, prompt: '', image: '' })
const batchData = ref('')

// 图片代理函数
const getProxyImageUrl = (imageUrl) => {
  if (!imageUrl) return ''
  // 如果是本地URL或已经是代理URL，直接返回
  if (imageUrl.startsWith('/') || imageUrl.includes('/api/image-proxy')) {
    return imageUrl
  }
  // 使用代理
  return `/api/image-proxy?url=${encodeURIComponent(imageUrl)}`
}

// 分页设置
const pendingPage = ref(1)
const runningPage = ref(1)
const successPage = ref(1)
const failedPage = ref(1)

// 每页数量设置
const pendingPageSize = ref(10)
const runningPageSize = ref(10)
const successPageSize = ref(10)
const failedPageSize = ref(10)

// 选中的任务
const pendingSelection = ref([])
const runningSelection = ref([])
const successSelection = ref([])
const failedSelection = ref([])

// 按状态分类任务
const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending'))
const runningTasks = computed(() => tasks.value.filter(t => t.status === 'running'))
const successTasks = computed(() => tasks.value.filter(t => t.status === 'success' || t.status === 'published'))
const failedTasks = computed(() => tasks.value.filter(t => t.status === 'failed'))

// 分页后的数据
const paginatedPendingTasks = computed(() => {
  const start = (pendingPage.value - 1) * pendingPageSize.value
  return pendingTasks.value.slice(start, start + pendingPageSize.value)
})

const paginatedRunningTasks = computed(() => {
  const start = (runningPage.value - 1) * runningPageSize.value
  return runningTasks.value.slice(start, start + runningPageSize.value)
})

const paginatedSuccessTasks = computed(() => {
  const start = (successPage.value - 1) * successPageSize.value
  return successTasks.value.slice(start, start + successPageSize.value)
})

const paginatedFailedTasks = computed(() => {
  const start = (failedPage.value - 1) * failedPageSize.value
  return failedTasks.value.slice(start, start + failedPageSize.value)
})

// 选择处理函数
const handlePendingSelection = (selection) => {
  pendingSelection.value = selection
}

const handleRunningSelection = (selection) => {
  runningSelection.value = selection
}

const handleSuccessSelection = (selection) => {
  successSelection.value = selection
}

const handleFailedSelection = (selection) => {
  failedSelection.value = selection
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待执行',
    running: '执行中',
    success: '成功',
    failed: '失败'
  }
  return texts[status] || status
}

const loadAccounts = async () => {
  try {
    const res = await api.getAccounts()
    if (res.success) {
      accounts.value = res.data
    }
  } catch (error) {
    ElMessage.error('加载账号列表失败')
  }
}

const loadTasks = async () => {
  try {
    const res = await api.getTasks()
    if (res.success) {
      tasks.value = res.data
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  }
}

const importTasks = async () => {
  try {
    let tasksToImport = []
    
    if (importMethod.value === 'manual') {
      if (!taskImport.value.prompt) {
        ElMessage.warning('请输入提示词')
        return
      }
      tasksToImport = [taskImport.value]
    } else {
      const lines = batchData.value.trim().split('\n')
      tasksToImport = lines.map(line => {
        const [prompt, image] = line.split('|').map(s => s.trim())
        return { 
          account_id: taskImport.value.account_id || null,
          profile_id: null,
          prompt, 
          image: image || null 
        }
      })
    }
    
    const res = await api.importTasks(tasksToImport)
    if (res.success) {
      ElMessage.success(res.message)
      showImportDialog.value = false
      taskImport.value = { account_id: null, prompt: '', image: '' }
      batchData.value = ''
      loadTasks()
    }
  } catch (error) {
    ElMessage.error('导入失败')
  }
}

const executeTask = async (taskId) => {
  try {
    const res = await api.executeTask(taskId)
    if (res.success) {
      ElMessage.success(res.message)
      setTimeout(loadTasks, 1000)
    }
  } catch (error) {
    ElMessage.error('执行失败')
  }
}

const deleteTask = async (taskId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await api.deleteTask(taskId)
    if (res.success) {
      ElMessage.success('任务已删除')
      loadTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const retryTask = async (taskId) => {
  try {
    const res = await api.retryTask(taskId)
    if (res.success) {
      ElMessage.success('任务已重置，将重新执行')
      loadTasks()
    }
  } catch (error) {
    ElMessage.error('重试失败')
  }
}

const terminateTask = async (taskId) => {
  try {
    await ElMessageBox.confirm('确定要终止这个任务吗？任务将退回到待处理队列。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await api.terminateTask(taskId)
    if (res.success) {
      ElMessage.success('任务已终止并退回到待处理队列')
      loadTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('终止失败')
    }
  }
}

const openVideo = (url) => {
  window.open(url, '_blank')
}

const handleFileUpload = async (file) => {
  try {
    const res = await api.importTasksFromFile(file)
    if (res.success) {
      ElMessage.success(res.message)
      loadTasks()
    }
  } catch (error) {
    ElMessage.error('文件上传失败')
  }
  return false // 阻止默认上传行为
}

// 批量删除任务
const batchDeleteTasks = async (selection) => {
  if (selection.length === 0) {
    ElMessage.warning('请先选择任务')
    return
  }
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selection.length} 个任务吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const taskIds = selection.map(t => t.id)
    const res = await api.batchDeleteTasks(taskIds)
    if (res.success) {
      ElMessage.success(`已删除 ${selection.length} 个任务`)
      loadTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

// 批量重试任务
const batchRetryTasks = async (selection) => {
  if (selection.length === 0) {
    ElMessage.warning('请先选择任务')
    return
  }
  
  try {
    const taskIds = selection.map(t => t.id)
    const res = await api.batchRetryTasks(taskIds)
    if (res.success) {
      ElMessage.success(`已重置 ${selection.length} 个任务`)
      loadTasks()
    }
  } catch (error) {
    ElMessage.error('批量重试失败')
  }
}

// 批量终止任务
const batchTerminateTasks = async (selection) => {
  if (selection.length === 0) {
    ElMessage.warning('请先选择任务')
    return
  }
  
  try {
    await ElMessageBox.confirm(`确定要终止选中的 ${selection.length} 个任务吗？任务将退回到待处理队列。`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 逐个终止任务
    let successCount = 0
    for (const task of selection) {
      try {
        const res = await api.terminateTask(task.id)
        if (res.success) {
          successCount++
        }
      } catch (error) {
        console.error(`终止任务 ${task.id} 失败:`, error)
      }
    }
    
    if (successCount > 0) {
      ElMessage.success(`已终止 ${successCount} 个任务`)
      loadTasks()
    } else {
      ElMessage.error('批量终止失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量终止失败')
    }
  }
}

onMounted(() => {
  loadAccounts()
  loadTasks()
  
  // 每5秒刷新一次
  setInterval(loadTasks, 5000)
})
</script>

<style scoped>
.tasks-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
}
</style>

