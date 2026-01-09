package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	stdruntime "runtime"
    "sync"
	"time"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

const CurrentVersion = "2.1.1"
const MetadataURL = "https://jnuexam.gubaiovo.com/metadata.json"

type PlatformInfo struct {
    Url      string `json:"url"`
    Checksum string `json:"checksum"`
}

type UpdateInfo struct {
    Version   string                  `json:"version"`
    Force     bool                    `json:"force"`
    Desc      string                  `json:"desc"`
    Platforms map[string]PlatformInfo `json:"platforms"`
}

type NoticeInfo struct {
    Show    bool   `json:"show"`
    Id      string `json:"id"`
    Title   string `json:"title"`
    Content string `json:"content"`
}

type AppMetadata struct {
    Notice NoticeInfo `json:"notice"`
    Update UpdateInfo `json:"update"`
}

type CheckResult struct {
    HasUpdate    bool       `json:"has_update"`
    CurrentVer   string     `json:"current_ver"`
    RemoteVer    string     `json:"remote_ver"`
    UpdateDesc   string     `json:"update_desc"`
    IsForce      bool       `json:"is_force"`
    DownloadURL  string     `json:"download_url"`
    Checksum     string     `json:"checksum"`
    Notice       NoticeInfo `json:"notice"`
}
type SourceConfig struct {
	JsonUrl string `json:"json_url"`
	FileKey string `json:"file_key"`
	DirUrl  string `json:"dir_url,omitempty"`
}

// type FileNode struct {
// 	Name         string      `json:"name"`
// 	Path         string      `json:"path"`
// 	Size         interface{} `json:"size"`
// 	Files        []*FileNode `json:"files,omitempty"`
// 	Dirs         []*FileNode `json:"dirs,omitempty"`
// 	CfUrl        string      `json:"cf_url,omitempty"`
// 	GithubRawUrl string      `json:"github_raw_url,omitempty"`
// }

type DownloadProgress struct {
	Filename   string  `json:"filename"`
	Percentage float64 `json:"percentage"`
}

type App struct {
	ctx context.Context
    dirCache  map[string]interface{}
    cacheLock sync.RWMutex
}

func NewApp() *App {
	return &App{
        dirCache: make(map[string]interface{}),
    }
}

func (a *App) startup(ctx context.Context) {
    a.ctx = ctx
    go a.cleanupOldFile()
}

func (a *App) cleanupOldFile() {
    exePath, err := os.Executable()
    if err != nil {
        return
    }
    oldPath := exePath + ".old"
    if _, err := os.Stat(oldPath); os.IsNotExist(err) {
        return
    }
    runtime.LogPrintf(a.ctx, "发现旧版本文件: %s，准备清理...", oldPath)
    for i := 0; i < 5; i++ {
        time.Sleep(1 * time.Second)
        err = os.Remove(oldPath)
        if err == nil {
            runtime.LogPrintf(a.ctx, "成功删除旧版本备份文件 (第 %d 次尝试)", i+1)
            return
        }
        runtime.LogPrintf(a.ctx, "删除失败 (尝试 %d/5): %v", i+1, err)
    }
    runtime.LogPrintf(a.ctx, "放弃清理：旧文件可能仍被占用")
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

func (a *App) FetchDirectory(url string) (interface{}, error) {
	a.cacheLock.RLock()
	if cached, ok := a.dirCache[url]; ok {
		a.cacheLock.RUnlock()
		runtime.LogPrintf(a.ctx, "命中缓存: %s", url)
		return cached, nil
	}
	a.cacheLock.RUnlock()

	runtime.LogPrintf(a.ctx, "正在获取目录(网络): %s", url)
	client := http.Client{Timeout: 15 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var root interface{}
	if err := json.NewDecoder(resp.Body).Decode(&root); err != nil {
		return nil, err
	}

	a.cacheLock.Lock()
	a.dirCache[url] = root
	a.cacheLock.Unlock()

	return root, nil
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

func (a *App) CheckAppUpdate() (*CheckResult, error) {
    runtime.LogPrintf(a.ctx, ">>>>> 开始检查更新，URL: %s", MetadataURL)

    client := http.Client{Timeout: 5 * time.Second}
    resp, err := client.Get(MetadataURL)
    if err != nil {
        runtime.LogPrintf(a.ctx, ">>>>> 网络请求失败: %v", err)
        return nil, err
    }
    defer resp.Body.Close()

    var meta AppMetadata
    if err := json.NewDecoder(resp.Body).Decode(&meta); err != nil {
        runtime.LogPrintf(a.ctx, ">>>>> JSON 解析失败: %v", err) 
        return nil, err
    }

    runtime.LogPrintf(a.ctx, ">>>>> 解析到的远程版本: %s", meta.Update.Version)

    platformKey := fmt.Sprintf("%s-%s", stdruntime.GOOS, stdruntime.GOARCH)
    runtime.LogPrintf(a.ctx, ">>>>> 当前系统生成的 Key: [%s]", platformKey)

    var target PlatformInfo
    var ok bool
    
    if meta.Update.Platforms != nil {
        target, ok = meta.Update.Platforms[platformKey]
        runtime.LogPrintf(a.ctx, ">>>>> Map 匹配结果: %v, 下载地址: %s", ok, target.Url)
    } else {
        runtime.LogPrintf(a.ctx, ">>>>> 警告: meta.Update.Platforms 为空 (JSON 结构可能不匹配)")
    }

    hasUpdate := (meta.Update.Version != CurrentVersion) && ok
    runtime.LogPrintf(a.ctx, ">>>>> 最终判定 hasUpdate: %v (本地: %s, 远程: %s)", hasUpdate, CurrentVersion, meta.Update.Version)

    return &CheckResult{
        HasUpdate:   hasUpdate,
        CurrentVer:  CurrentVersion,
        RemoteVer:   meta.Update.Version,
        UpdateDesc:  meta.Update.Desc,
        IsForce:     meta.Update.Force,
        DownloadURL: target.Url,
        Checksum:    target.Checksum,
        Notice:      meta.Notice,
    }, nil
}

func (a *App) PerformSelfUpdate(url string, checksum string) error {
    runtime.LogPrintf(a.ctx, "开始自动更新流程...")

    exePath, err := os.Executable()
    if err != nil {
        return fmt.Errorf("无法获取程序路径: %v", err)
    }
    
    dir := filepath.Dir(exePath)
    targetName := "JNU-EXAM-Downloader"
    if stdruntime.GOOS == "windows" {
        targetName += ".exe"
    }
    targetPath := filepath.Join(dir, targetName)
    tmpPath := filepath.Join(dir, "update.tmp")
    
    runtime.LogPrintf(a.ctx, "正在下载更新: %s", url)
    resp, err := http.Get(url)
    if err != nil {
        return fmt.Errorf("下载失败: %v", err)
    }
    defer resp.Body.Close()

    out, err := os.Create(tmpPath)
    if err != nil {
        return fmt.Errorf("无法创建临时文件: %v", err)
    }
    
    hasher := sha256.New()
    contentLen := resp.ContentLength
    
    buf := make([]byte, 32*1024)
    var downloaded int64 = 0
    
    for {
        n, readErr := resp.Body.Read(buf)
        if n > 0 {
            out.Write(buf[:n])
            hasher.Write(buf[:n])
            
            downloaded += int64(n)
            if contentLen > 0 {
                percent := (float64(downloaded) / float64(contentLen)) * 100
                runtime.EventsEmit(a.ctx, "update_progress", percent)
            }
        }
        if readErr == io.EOF {
            break
        }
        if readErr != nil {
            out.Close()
            return readErr
        }
    }
    out.Close()

    if checksum != "" {
        calculatedHash := hex.EncodeToString(hasher.Sum(nil))
        if calculatedHash != checksum {
            os.Remove(tmpPath)
            return fmt.Errorf("文件校验失败! 期望: %s, 实际: %s", checksum, calculatedHash)
        }
    }

    oldPath := exePath + ".old"
    
    os.Remove(oldPath)

    if err := os.Rename(exePath, oldPath); err != nil {
        os.Remove(tmpPath)
        return fmt.Errorf("无法重命名当前程序: %v", err)
    }

    if err := os.Rename(tmpPath, targetPath); err != nil {
        os.Rename(oldPath, exePath) 
        return fmt.Errorf("无法应用新文件: %v", err)
    }

    if stdruntime.GOOS != "windows" {
        os.Chmod(targetPath, 0755)
    }

    runtime.LogPrintf(a.ctx, "更新完成，准备重启: %s", targetPath)
    cmd := exec.Command(targetPath)
    cmd.Start()

    os.Exit(0)
    
    return nil
}