<script setup>
import { reactive, onMounted, ref, computed, watch } from 'vue'
import { FetchSourceList, FetchDirectory, DownloadFile, SelectSavePath, OpenFileDir } from '../wailsjs/go/main/App'
import { EventsOn } from '../wailsjs/runtime'
import FileTree from './components/FileTree.vue'

const Icons = {
  Sun: `<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  Moon: `<path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  Settings: `<path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  Search: `<path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  Download: `<path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  FolderOpen: `<path d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
  Refresh: `<path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
}

const DEFAULT_CONFIG_URL = "https://www.gubaiovo.com/jnu-exam/source_list.json"

const state = reactive({
  sources: {},
  currentSource: "",
  fileTree: {},
  allFlatFiles: [],
  selectedFile: null,
  isDownloading: false,
  progress: 0,
  status: "就绪",
  lastDownloadPath: "",
  configUrl: DEFAULT_CONFIG_URL,
  isDark: false, 
  showSettings: false 
})

// --- Resizable Sidebar Logic ---
const sidebarWidth = ref(300) 
const isResizing = ref(false)

function startResize() {
  isResizing.value = true
  document.addEventListener('mousemove', doResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function doResize(e) {
  if (isResizing.value) {
    let newWidth = e.clientX
    if (newWidth < 200) newWidth = 200
    if (newWidth > 600) newWidth = 600
    sidebarWidth.value = newWidth
  }
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', doResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const searchQuery = ref("")

// --- Lifecycle & Init ---
onMounted(async () => {
  const storedUrl = localStorage.getItem('custom_source_url')
  if (storedUrl) state.configUrl = storedUrl
  
  const storedTheme = localStorage.getItem('theme')
  if (storedTheme === 'dark') {
    state.isDark = true
    document.documentElement.classList.add('dark-theme')
  }

  await refreshSource()

  EventsOn("download_progress", (data) => {
    state.progress = data.percentage
    state.status = `正在下载: ${data.percentage.toFixed(1)}%`
  })
})


// 切换主题
function toggleTheme() {
  state.isDark = !state.isDark
  if (state.isDark) {
    document.documentElement.classList.add('dark-theme')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark-theme')
    localStorage.setItem('theme', 'light')
  }
}

// 刷新源列表
async function refreshSource() {
  try {
    state.status = "正在加载源列表..."
    state.sources = await FetchSourceList(state.configUrl)
    
    const keys = Object.keys(state.sources)
    if (keys.length > 0) {
      if (!state.sources[state.currentSource]) {
        state.currentSource = keys.find(k => k.toLowerCase().includes('r2')) || keys[0]
      }
      await loadDirectory()
    }
    state.status = "就绪"
  } catch (e) {
    state.status = "加载失败: " + e
  }
}

// 保存配置
function saveSettings() {
  if (!state.configUrl.trim()) {
    state.configUrl = DEFAULT_CONFIG_URL
  }
  localStorage.setItem('custom_source_url', state.configUrl)
  state.showSettings = false
  refreshSource()
}

// 扁平化数据
function flattenFiles(node, list) {
  if (node.files) list.push(...node.files)
  if (node.dirs) node.dirs.forEach(d => flattenFiles(d, list))
}

// 加载目录
async function loadDirectory() {
  if (!state.currentSource) return
  
  try {
    state.status = "正在获取目录..."
    state.fileTree = {}
    state.selectedFile = null
    state.allFlatFiles = []
    
    const config = state.sources[state.currentSource]
    const data = await FetchDirectory(config.json_url)
    
    if (!data.name) data.name = "全部文件"
    
    const flatList = []
    flattenFiles(data, flatList)
    state.allFlatFiles = flatList
    state.fileTree = data
    state.status = `已加载 ${state.currentSource}`
  } catch (e) {
    state.status = "目录加载失败: " + e
  }
}

// 搜索
const isSearching = computed(() => searchQuery.value.trim().length > 0)
const searchResults = computed(() => {
  if (!isSearching.value) return []
  const q = searchQuery.value.toLowerCase()
  return state.allFlatFiles.filter(f => f.name.toLowerCase().includes(q))
})

// 下载
async function download() {
  if (!state.selectedFile || state.isDownloading) return
  const config = state.sources[state.currentSource]
  const url = state.selectedFile[config.file_key]
  
  if (!url) return alert("无下载链接")

  const savePath = await SelectSavePath(state.selectedFile.name)
  if (!savePath) return

  try {
    state.isDownloading = true
    state.progress = 0
    await DownloadFile(url, savePath)
    state.status = "下载完成"
    state.progress = 100
    state.lastDownloadPath = savePath
  } catch (e) {
    state.status = "错误: " + e
  } finally {
    state.isDownloading = false
  }
}

function formatSize(size) {
  if (!size) return '-'
  const num = Number(size)
  if (num >= 1048576) return (num / 1048576).toFixed(2) + ' MB'
  if (num >= 1024) return (num / 1024).toFixed(2) + ' KB'
  return num + ' B'
}

// 图标颜色
function getFileIconColor(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (ext === 'pdf') return '#ef4444' // red
  if (['zip', 'rar', '7z'].includes(ext)) return '#f59e0b' // amber
  if (['doc', 'docx'].includes(ext)) return '#3b82f6' // blue
  if (['xls', 'xlsx'].includes(ext)) return '#10b981' // green
  if (['ppt', 'pptx'].includes(ext)) return '#f97316' // orange
  return 'var(--text-secondary)'
}
</script>

<template>
  <div class="app-container">
    <div class="sidebar" :style="{ width: sidebarWidth + 'px' }">
      <div class="sidebar-header">
        <div class="brand">
          <span class="brand-icon">🎓</span>
          <span class="brand-text">期末无挂</span>
        </div>
        <div class="header-actions">
          <button class="icon-btn" @click="toggleTheme" title="切换主题">
            <svg viewBox="0 0 24 24" fill="none" class="w-5 h-5" v-html="state.isDark ? Icons.Moon : Icons.Sun"></svg>
          </button>
          <button class="icon-btn" @click="state.showSettings = true" title="设置">
            <svg viewBox="0 0 24 24" fill="none" class="w-5 h-5" v-html="Icons.Settings"></svg>
          </button>
        </div>
      </div>

      <div class="sidebar-controls">
        <div class="select-wrapper">
          <select v-model="state.currentSource" @change="loadDirectory" class="custom-select">
            <option v-for="(val, key) in state.sources" :key="key" :value="key">{{ key }}</option>
          </select>
          <svg class="select-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M6 9l6 6 6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        
        <div class="search-wrapper">
          <svg viewBox="0 0 24 24" fill="none" class="search-icon" v-html="Icons.Search"></svg>
          <input v-model="searchQuery" placeholder="搜索文件..." class="search-input">
        </div>
      </div>

      <div class="sidebar-list">
        <transition name="fade" mode="out-in">
          <div v-if="isSearching" key="search" class="search-results">
            <div v-if="searchResults.length === 0" class="empty-tip">未找到文件</div>
            <div 
              v-for="(file, idx) in searchResults" 
              :key="'s-'+idx" 
              class="list-item"
              :class="{ active: state.selectedFile === file }"
              @click="state.selectedFile = file"
            >
              <span class="file-icon-mini">📄</span>
              <div class="list-info">
                <div class="name">{{ file.name }}</div>
                <div class="path">{{ file.path }}</div>
              </div>
            </div>
          </div>

          <div v-else-if="state.fileTree.name" key="tree">
            <FileTree :node="state.fileTree" @select-file="(f) => state.selectedFile = f" />
          </div>
          
          <div v-else key="loading" class="loading-state">
            <div class="spinner"></div>
            <p>正在加载目录...</p>
          </div>
        </transition>
      </div>
    </div>
    
    <div class="resize-handle" @mousedown="startResize"></div>

    <div class="main-content">
      <transition name="slide-up" mode="out-in">
        <div v-if="state.selectedFile" :key="state.selectedFile.path" class="file-card align-left">
          <div class="file-preview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="preview-icon" :style="{ color: getFileIconColor(state.selectedFile.name) }">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"></path>
              <path d="M14 2v6h6"></path>
              <path d="M16 13H8"></path>
              <path d="M16 17H8"></path>
              <path d="M10 9H8"></path>
            </svg>
          </div>

          <h2 class="file-title">{{ state.selectedFile.name }}</h2>
          
          <div class="file-meta">
            <div class="meta-item">
              <span class="label">路径</span>
              <span class="val">{{ state.selectedFile.path }}</span>
            </div>
            <div class="meta-item">
              <span class="label">大小</span>
              <span class="val">{{ formatSize(state.selectedFile.size) }}</span>
            </div>
          </div>

          <div class="action-buttons">
            <button 
              class="btn-primary" 
              @click="download" 
              :disabled="state.isDownloading"
            >
              <svg v-if="!state.isDownloading" viewBox="0 0 24 24" fill="none" class="btn-icon" v-html="Icons.Download"></svg>
              <span v-else class="spinner-mini"></span>
              {{ state.isDownloading ? '下载中...' : '下载文件' }}
            </button>

            <button 
              v-if="state.progress === 100 && state.lastDownloadPath" 
              class="btn-secondary" 
              @click="OpenFileDir(state.lastDownloadPath)"
            >
              <svg viewBox="0 0 24 24" fill="none" class="btn-icon" v-html="Icons.FolderOpen"></svg>
              打开位置
            </button>
          </div>

          <div class="progress-wrapper" :class="{ active: state.progress > 0 && state.progress < 100 }">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: state.progress + '%' }"></div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-illustration">📚</div>
          <p>从左侧选择一个文件开始下载</p>
        </div>
      </transition>
      
      <div class="status-bar">{{ state.status }}</div>
    </div>

    <transition name="fade">
      <div v-if="state.showSettings" class="modal-overlay" @click.self="state.showSettings = false">
        <div class="modal">
          <div class="modal-header">
            <h3>⚙️ 设置</h3>
            <button class="close-btn" @click="state.showSettings = false">×</button>
          </div>
          <div class="modal-body">
            <label>源列表配置 URL</label>
            <input v-model="state.configUrl" class="modal-input" placeholder="输入 JSON 地址...">
            <p class="modal-hint">通常你不需要修改此项，除非你有自定义的源。</p>
          </div>
          <div class="modal-footer">
            <button class="btn-text" @click="state.configUrl = DEFAULT_CONFIG_URL">恢复默认</button>
            <button class="btn-primary" @click="saveSettings">保存并刷新</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style>
:root {
  /* 浅色主题 (默认) */
  --bg-primary: #ffffff;
  --bg-secondary: #f3f4f6;
  --bg-tertiary: #e5e7eb;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --accent-color: #3b82f6;
  --accent-hover: #2563eb;
  --border-color: #e5e7eb;
  --card-bg: #ffffff;
  --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --input-bg: #ffffff;
}

:root.dark-theme {
  /* 深色主题 (深蓝色) */
  --bg-primary: #020617;
  --bg-secondary: #0f172a; 
  --bg-tertiary: #1e293b;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-color: #3b82f6; 
  --accent-hover: #60a5fa;
  --border-color: #1e293b;
  --card-bg: #0f172a;
  --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
  --input-bg: #1e293b;
}

* { box-sizing: border-box; }
body { 
  margin: 0; 
  font-family: 'Segoe UI', system-ui, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
  overflow: hidden;
}

.app-container { display: flex; height: 100vh; width: 100vw; }

.sidebar { 
  background: var(--bg-secondary); 
  border-right: 1px solid var(--border-color); 
  display: flex; 
  flex-direction: column; 
  transition: background-color 0.3s;
  position: relative; 
  z-index: 50;  
  flex-shrink: 0; 
}

.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
}

.brand { 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  font-weight: bold; 
  font-size: 1.1em;
  color: var(--text-primary);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.w-5 { width: 20px; }
.h-5 { height: 20px; }

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 6px; border-radius: 4px;
  transition: background 0.2s;
}

.icon-btn:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.sidebar-controls { 
  padding: 12px; 
  display: flex; 
  flex-direction: column; 
  gap: 10px; 
  position: relative; 
  z-index: 51; 
  overflow: visible;
}

.search-wrapper { position: relative; }
.search-icon { position: absolute; left: 8px; top: 8px; width: 16px; height: 16px; color: var(--text-secondary); }
.search-input {
  width: 100%; padding: 6px 6px 6px 30px; border-radius: 6px;
  border: 1px solid var(--border-color); background: var(--input-bg); color: var(--text-primary);
  outline: none; transition: border-color 0.2s;
}
.search-input:focus { border-color: var(--accent-color); }

.sidebar-list { flex: 1; overflow-y: auto; padding: 0; }

/* 列表项样式 */
.list-item {
  padding: 8px 16px; display: flex; align-items: center; gap: 10px; cursor: pointer;
  border-bottom: 1px solid transparent; transition: background 0.1s;
}
.list-item:hover { background: var(--bg-tertiary); }
.list-item.active { background: var(--accent-color); color: white; }
.list-item.active .path { color: rgba(255,255,255,0.8); }
.list-info { overflow: hidden; }
.list-info .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px; }
.list-info .path { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.empty-tip { text-align: center; color: var(--text-secondary); padding: 20px; font-size: 13px; }

/* 加载动画 */
.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100px; color: var(--text-secondary); }
.spinner {
  width: 20px; height: 20px; border: 2px solid var(--bg-tertiary); border-top-color: var(--accent-color);
  border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 主内容 */
.main-content { 
  flex: 1; position: relative; background: var(--bg-primary); 
  display: flex; align-items: center; justify-content: center;
}

.file-card {
  width: 100%;
  max-width: 600px;
  background: var(--card-bg); 
  padding: 40px; 
  border-radius: 16px;
  box-shadow: var(--card-shadow); 
  text-align: center;
  border: 1px solid var(--border-color);
  transition: all 0.3s;
}

.file-card .file-preview { 
  display: flex; 
  justify-content: center; 
  margin-bottom: 20px; 
}

.file-title { 
  margin: 0 0 20px 0; 
  font-size: 1.5em; 
  word-break: break-all; 
  text-align: center;
  color: var(--text-primary);
}
.preview-icon { width: 80px; height: 80px; }

.file-meta { text-align: left; background: var(--bg-secondary); padding: 15px; border-radius: 8px; margin-bottom: 30px; }
.meta-item { display: flex; margin-bottom: 8px; font-size: 13px; }
.meta-item:last-child { margin-bottom: 0; }
.meta-item .label { width: 40px; color: var(--text-secondary); }
.meta-item .val { 
  flex: 1; 
  word-break: break-all; 
  font-family: monospace;
  color: var(--text-primary);
}
.action-buttons { display: flex; flex-direction: column; gap: 10px; }
.btn-primary, .btn-secondary {
  padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none;
  display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity 0.2s;
}
.btn-primary { background: var(--accent-color); color: white; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }
.btn-secondary:hover { opacity: 0.9; }
.btn-icon { width: 18px; height: 18px; stroke-width: 2.5; }

.spinner-mini {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}

.progress-wrapper { height: 4px; background: var(--bg-tertiary); border-radius: 2px; overflow: hidden; margin-top: 20px; opacity: 0; transition: opacity 0.3s; }
.progress-wrapper.active { opacity: 1; }
.progress-fill { height: 100%; background: var(--accent-color); transition: width 0.3s; }

.empty-state { text-align: center; color: var(--text-secondary); }
.empty-illustration { font-size: 60px; margin-bottom: 10px; opacity: 0.5; }

.status-bar { 
  position: absolute; bottom: 0; left: 0; right: 0; 
  padding: 6px 16px; font-size: 12px; color: var(--text-secondary); 
  background: var(--bg-secondary); border-top: 1px solid var(--border-color);
}

/* 弹窗 */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100;
  backdrop-filter: blur(2px);
}
.modal {
  background: var(--card-bg); 
  width: 400px; 
  border-radius: 12px; 
  box-shadow: var(--card-shadow);
  border: 1px solid var(--border-color); 
  overflow: hidden;
  color: var(--text-primary); 
}
.modal-header { 
  padding: 15px 20px; 
  border-bottom: 1px solid var(--border-color); 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
}
.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}
.modal-body label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-secondary); }
.modal-body { padding: 20px; }
.modal-input {
  width: 100%; padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);
  background: var(--input-bg); color: var(--text-primary); margin-top: 8px;
}
.modal-hint { font-size: 12px; color: var(--text-secondary); margin-top: 8px; }
.modal-footer { padding: 15px 20px; background: var(--bg-secondary); display: flex; justify-content: flex-end; gap: 10px; }
.btn-text { background: none; border: none; color: var(--text-secondary); cursor: pointer; }
.btn-text:hover { color: var(--text-primary); }

/* Vue 过渡动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); }
.slide-up-enter-from { opacity: 0; transform: translateY(20px); }
.slide-up-leave-to { opacity: 0; transform: translateY(-20px); }

.resize-handle {
  width: 5px;
  background: transparent;
  cursor: col-resize;
  transition: background 0.2s;
  z-index: 100;
  margin-left: -2px; 
}
.resize-handle:hover, .resize-handle:active {
  background: var(--accent-color);
}

/* --- 下拉菜单美化 --- */
.select-wrapper {
  position: relative;
  width: 100%;
}

.custom-select {
  width: 100%;
  padding: 10px 32px 10px 12px; /* 右侧留出箭头位置 */
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background-color: var(--input-bg);
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  cursor: pointer;
  appearance: none; /* 关键：去除系统默认丑陋样式 */
  -webkit-appearance: none;
  transition: border-color 0.2s, background-color 0.2s;
}

.custom-select:hover {
  border-color: var(--text-secondary);
}

.custom-select:focus {
  border-color: var(--accent-color);
}

.custom-select option {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  padding: 10px;
}

/* 自定义箭头定位 */
.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
  pointer-events: none; 
}
</style>