<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#409EFF"><User /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.accounts.total }}</div>
              <div class="stat-label">总账号数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#67C23A"><CircleCheck /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.accounts.active }}</div>
              <div class="stat-label">活跃账号</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#E6A23C"><List /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.tasks.total }}</div>
              <div class="stat-label">总任务数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#67C23A"><SuccessFilled /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.tasks.success }}</div>
              <div class="stat-label">成功任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#909399"><Clock /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.tasks.pending }}</div>
              <div class="stat-label">待执行</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#409EFF"><Loading /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.tasks.running }}</div>
              <div class="stat-label">执行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#F56C6C"><CircleClose /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.tasks.failed }}</div>
              <div class="stat-label">失败任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon class="stat-icon" color="#67C23A"><TrendCharts /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ successRate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span>系统配置</span>
          </template>
          
          <el-form label-width="200px">
            <el-form-item label="后端关闭时自动关闭窗口">
              <el-switch 
                v-model="config.auto_close_windows_on_shutdown"
                @change="updateConfig"
                active-text="开启"
                inactive-text="关闭"
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                开启后，停止后端服务时会自动关闭所有通过系统打开的窗口
              </div>
            </el-form-item>
            
            <el-form-item label="启动时自动检测已打开窗口">
              <el-switch 
                v-model="config.auto_detect_open_windows_on_startup"
                @change="updateConfig"
                active-text="开启"
                inactive-text="关闭"
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px;">
                开启后，启动后端服务时会自动检测并连接到已打开的窗口（需重启后端生效）
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const stats = ref({
  accounts: { total: 0, active: 0 },
  tasks: { total: 0, pending: 0, running: 0, success: 0, failed: 0 }
})

const config = ref({
  auto_close_windows_on_shutdown: true,
  auto_detect_open_windows_on_startup: true
})

const successRate = computed(() => {
  const total = stats.value.tasks.success + stats.value.tasks.failed
  if (total === 0) return 0
  return ((stats.value.tasks.success / total) * 100).toFixed(1)
})

const loadStats = async () => {
  try {
    const res = await api.getStats()
    if (res.success) {
      stats.value = res.data
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const loadConfig = async () => {
  try {
    const res = await api.getConfig()
    if (res.success) {
      config.value = res.data
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const updateConfig = async () => {
  try {
    const res = await api.updateConfig(config.value)
    if (res.success) {
      ElMessage.success('配置已更新')
    }
  } catch (error) {
    ElMessage.error('更新配置失败')
  }
}

onMounted(() => {
  loadStats()
  loadConfig()
  // 每10秒刷新一次统计
  setInterval(loadStats, 10000)
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  font-size: 48px;
  margin-right: 20px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>
