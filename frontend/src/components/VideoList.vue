<template>
  <div class="video-list">
    <el-empty v-if="videos.length === 0" description="暂无视频数据" />
    
    <el-table v-else :data="videos" stripe>
      <el-table-column prop="url" label="视频链接" min-width="300">
        <template #default="{ row }">
          <el-link :href="row.url" target="_blank" type="primary">
            {{ row.url }}
          </el-link>
        </template>
      </el-table-column>
      
      <el-table-column prop="prompt" label="提示词" min-width="200" show-overflow-tooltip />
      
      <el-table-column label="状态" width="100">
        <template #default>
          <el-tag v-if="type === 'published'" type="success">已发布</el-tag>
          <el-tag v-else-if="type === 'generating'" type="warning">生成中</el-tag>
          <el-tag v-else type="info">未发布</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="published" label="是否发布" width="100">
        <template #default="{ row }">
          <el-icon v-if="row.published" color="#67C23A" :size="20">
            <Check />
          </el-icon>
          <el-icon v-else color="#909399" :size="20">
            <Close />
          </el-icon>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button size="small" @click="copyUrl(row.url)">
            复制链接
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'

defineProps({
  videos: {
    type: Array,
    default: () => []
  },
  type: {
    type: String,
    default: 'published'
  }
})

const copyUrl = (url) => {
  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('链接已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}
</script>

<style scoped>
.video-list {
  min-height: 200px;
}
</style>
