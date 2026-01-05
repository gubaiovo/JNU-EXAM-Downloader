package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	stdruntime "runtime" //以此别名引入标准库 runtime，避免与 wails runtime 冲突
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// SourceConfig, FileNode, DownloadProgress 保持不变
type SourceConfig struct {
	JsonUrl string `json:"json_url"`
	FileKey string `json:"file_key"`
	DirUrl  string `json:"dir_url,omitempty"`
}

type FileNode struct {
	Name         string      `json:"name"`
	Path         string      `json:"path"`
	Size         interface{} `json:"size"`
	Files        []*FileNode `json:"files,omitempty"`
	Dirs         []*FileNode `json:"dirs,omitempty"`
	CfUrl        string      `json:"cf_url,omitempty"`
	GithubRawUrl string      `json:"github_raw_url,omitempty"`
}

type DownloadProgress struct {
	Filename   string  `json:"filename"`
	Percentage float64 `json:"percentage"`
}

type App struct {
	ctx context.Context
}

func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

// --- 核心业务逻辑 ---

func (a *App) FetchSourceList(url string) (map[string]SourceConfig, error) {
	runtime.LogPrintf(a.ctx, "正在获取源列表: %s", url)
	client := http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var sources map[string]SourceConfig
	if err := json.NewDecoder(resp.Body).Decode(&sources); err != nil {
		return nil, err
	}
	for k, v := range sources {
		if v.JsonUrl == "" && v.DirUrl != "" {
			v.JsonUrl = v.DirUrl
			sources[k] = v
		}
	}
	return sources, nil
}

func (a *App) FetchDirectory(url string) (*FileNode, error) {
	runtime.LogPrintf(a.ctx, "正在获取目录: %s", url)
	client := http.Client{Timeout: 15 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var root FileNode
	if err := json.NewDecoder(resp.Body).Decode(&root); err != nil {
		return nil, err
	}
	return &root, nil
}

// DownloadFile 保持原有逻辑，但由前端传入完整路径
func (a *App) DownloadFile(url string, savePath string) error {
	runtime.LogPrintf(a.ctx, "开始下载: %s -> %s", url, savePath)

	if err := os.MkdirAll(filepath.Dir(savePath), 0755); err != nil {
		return err
	}

	out, err := os.Create(savePath)
	if err != nil {
		return err
	}
	defer out.Close()

	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	counter := &WriteCounter{
		Total:    float64(resp.ContentLength),
		Filename: filepath.Base(savePath),
		Ctx:      a.ctx,
	}

	_, err = io.Copy(out, io.TeeReader(resp.Body, counter))
	return err
}

// --- 新增功能 ---

// SelectSavePath 唤起系统保存文件对话框
func (a *App) SelectSavePath(defaultName string) string {
	selection, err := runtime.SaveFileDialog(a.ctx, runtime.SaveDialogOptions{
		Title:            "另存为",
		DefaultFilename:  defaultName,
		DefaultDirectory: "", // 默认为空，系统会自动记忆上次位置或使用文档目录
	})
	if err != nil {
		return ""
	}
	return selection
}

// OpenFileDir 打开文件所在的资源管理器
func (a *App) OpenFileDir(filePath string) error {
	runtime.LogPrintf(a.ctx, "尝试打开文件夹: %s", filePath)
	
	// 获取目录路径
	dir := filepath.Dir(filePath)
	
	var cmd *exec.Cmd
	
	switch stdruntime.GOOS {
	case "windows":
		// Windows: explorer /select,filename 会选中该文件
		cmd = exec.Command("explorer", "/select,", filePath)
	case "darwin":
		// macOS
		cmd = exec.Command("open", "-R", filePath)
	case "linux":
		// Linux: 通常使用 xdg-open 打开目录
		cmd = exec.Command("xdg-open", dir)
	default:
		return fmt.Errorf("unsupported platform")
	}
	
	return cmd.Start()
}

// --- 进度条辅助 ---

type WriteCounter struct {
	Total      float64
	Downloaded float64
	Filename   string
	Ctx        context.Context
}

func (wc *WriteCounter) Write(p []byte) (int, error) {
	n := len(p)
	wc.Downloaded += float64(n)
	percent := (wc.Downloaded / wc.Total) * 100
	
	// 简单限流：实际生产中可以使用 ticker 减少事件发送频率
	// 这里为了演示流畅性，暂时全发
	runtime.EventsEmit(wc.Ctx, "download_progress", DownloadProgress{
		Filename:   wc.Filename,
		Percentage: percent,
	})
	return n, nil
}