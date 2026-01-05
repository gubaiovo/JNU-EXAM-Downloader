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
	stdruntime "runtime"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

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

func (a *App) SelectSavePath(defaultName string) string {
	selection, err := runtime.SaveFileDialog(a.ctx, runtime.SaveDialogOptions{
		Title:            "另存为",
		DefaultFilename:  defaultName,
		DefaultDirectory: "",
	})
	if err != nil {
		return ""
	}
	return selection
}

func (a *App) OpenFileDir(filePath string) error {
	runtime.LogPrintf(a.ctx, "尝试打开文件夹: %s", filePath)
	
	dir := filepath.Dir(filePath)
	
	var cmd *exec.Cmd
	
	switch stdruntime.GOOS {
	case "windows":
		cmd = exec.Command("explorer", "/select,", filePath)
	case "darwin":
		cmd = exec.Command("open", "-R", filePath)
	case "linux":
		cmd = exec.Command("xdg-open", dir)
	default:
		return fmt.Errorf("unsupported platform")
	}
	
	return cmd.Start()
}


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
	
	runtime.EventsEmit(wc.Ctx, "download_progress", DownloadProgress{
		Filename:   wc.Filename,
		Percentage: percent,
	})
	return n, nil
}