<template>
  <div class="accounts-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>账号列表</span>
          <el-button type="primary" @click="showImportDialog = true">
            <el-icon><Plus /></el-icon>
            导入账号
          </el-button>
        </div>
      </template>
      
      <el-table :data="accounts" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="profile_id" label="窗口ID" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '活跃' : '空闲' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="viewTasks(row.id)">查看任务</el-button>
            <el-button size="small" type="danger" @click="deleteAccount(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入账号" width="600px">
      <el-form>
        <el-form-item label="导入方式">
          <el-radio-group v-model="importMethod">
            <el-radio label="manual">手动输入</el-radio>
            <el-radio label="batch">批量导入</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <template v-if="importMethod === 'manual'">
          <el-form-item label="用户名">
            <el-input v-model="newAccount.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="newAccount.password" type="password" placeholder="请输入密码" />
          </el-form-item>
          <el-form-item label="窗口ID">
            <el-input-number v-model="newAccount.profile_id" :min="1" placeholder="请输入窗口ID" />
          </el-form-item>
        </template>
        
        <template v-else>
          <el-form-item label="批量数据">
            <el-input
              v-model="batchData"
              type="textarea"
              :rows="10"
              placeholder="格式：用户名,密码,窗口ID（每行一个账号）&#10;示例：&#10;user1,pass1,23&#10;user2,pass2,24"
            />
          </el-form-item>
        </template>
      </el-form>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importAccounts">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const accounts = ref([])
const showImportDialog = ref(false)
const importMethod = ref('manual')
const newAccount = ref({ username: '', password: '', profile_id: null })
const batchData = ref('')

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

const importAccounts = async () => {
  try {
    let accountsToImport = []
    
    if (importMethod.value === 'manual') {
      if (!newAccount.value.username || !newAccount.value.password) {
        ElMessage.warning('请填写完整信息')
        return
      }
      accountsToImport = [newAccount.value]
    } else {
      const lines = batchData.value.trim().split('\n')
      accountsToImport = lines.map(line => {
        const [username, password, profile_id] = line.split(',').map(s => s.trim())
        return { username, password, profile_id: profile_id ? parseInt(profile_id) : null }
      })
    }
    
    const res = await api.importAccounts(accountsToImport)
    if (res.success) {
      ElMessage.success(res.message)
      showImportDialog.value = false
      newAccount.value = { username: '', password: '', profile_id: null }
      batchData.value = ''
      loadAccounts()
    }
  } catch (error) {
    ElMessage.error('导入失败')
  }
}

const deleteAccount = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除此账号吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await api.deleteAccount(id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadAccounts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewTasks = (accountId) => {
  router.push({ path: '/tasks', query: { account_id: accountId } })
}

onMounted(() => {
  loadAccounts()
})
</script>

<style scoped>
.accounts-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
