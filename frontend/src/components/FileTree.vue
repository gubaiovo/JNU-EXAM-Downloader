<script setup>
import { ref, computed } from 'vue'

defineOptions({ name: 'FileTree' })

const props = defineProps({
  node: Object, 
  depth: { type: Number, default: 0 }
})

const emit = defineEmits(['select-file'])
const isOpen = ref(false)

// 构建树逻辑保持不变...
function buildTree(flatData) {
  const rootDirs = [] 
  const dirMap = {} 
  const sourceDirs = flatData.dirs || []

  sourceDirs.forEach(dir => {
    dirMap[dir.path] = {
      ...dir, dirs: [], files: dir.files || [] 
    }
  })

  sourceDirs.forEach(dir => {
    const currentNode = dirMap[dir.path]
    const lastSlashIndex = dir.path.lastIndexOf('/')
    const parentPath = lastSlashIndex === -1 ? '' : dir.path.substring(0, lastSlashIndex)
    if (dirMap[parentPath]) dirMap[parentPath].dirs.push(currentNode)
    else rootDirs.push(currentNode)
  })

  return { name: '全部文件', path: '', dirs: rootDirs, files: flatData.files || [] }
}

const structuredNode = computed(() => {
  if (props.depth === 0 && props.node) return buildTree(props.node)
  return props.node || { dirs: [], files: [] }
})

const hasChildren = computed(() => {
  const n = structuredNode.value
  return (n.dirs && n.dirs.length > 0) || (n.files && n.files.length > 0)
})

function toggle() {
  if (hasChildren.value) isOpen.value = !isOpen.value
}
</script>

<template>
  <div class="tree-container">
    <div 
      class="node-row" 
      :style="{ paddingLeft: (depth * 16 + 10) + 'px' }" 
      @click="toggle"
      :class="{ 'clickable': hasChildren, 'active': isOpen }"
    >
      <span class="icon-wrap" :class="{ 'rotate': isOpen }" v-if="hasChildren">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M9 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span class="folder-icon" v-else>•</span>

      <span class="icon-folder">
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" class="text-folder">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
        </svg>
      </span>
      
      <span class="node-name" :title="structuredNode.path">{{ structuredNode.name || 'Root' }}</span>
    </div>

    <div v-if="isOpen" class="children-wrap">
      <FileTree 
        v-for="(dir, index) in structuredNode.dirs" 
        :key="'dir-'+index" 
        :node="dir" 
        :depth="depth + 1"
        @select-file="(f) => emit('select-file', f)" 
      />
      
      <div 
        v-for="(file, index) in structuredNode.files" 
        :key="'file-'+index" 
        class="file-row" 
        :style="{ paddingLeft: ((depth + 1) * 16 + 28) + 'px' }"
        @click.stop="emit('select-file', file)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" class="text-file">
          <path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z" stroke-width="2"/>
          <path d="M13 2v7h7" stroke-width="2"/>
        </svg>
        <span class="file-name" :title="file.name">{{ file.name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tree-container { user-select: none; font-size: 14px; color: var(--text-primary); }

.node-row, .file-row {
  display: flex; align-items: center; padding-top: 6px; padding-bottom: 6px; padding-right: 10px;
  cursor: default; transition: background-color 0.1s; border-radius: 4px; margin: 1px 4px;
}
.node-row:hover, .file-row:hover { background-color: var(--bg-tertiary); }
.node-row.clickable { cursor: pointer; }

.icon-wrap { 
  width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; 
  margin-right: 4px; transition: transform 0.2s; color: var(--text-secondary);
}
.icon-wrap.rotate { transform: rotate(90deg); }
.folder-icon { width: 16px; text-align: center; color: var(--text-secondary); margin-right: 4px; }

.icon-folder { margin-right: 6px; display: flex; align-items: center; }
.text-folder { color: #f59e0b; } /* Amber-500 */
.text-file { color: var(--text-secondary); margin-right: 8px; }

.node-name, .file-name {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;
}
.file-row { color: var(--text-secondary); }
.file-row:hover { color: var(--text-primary); }
</style>