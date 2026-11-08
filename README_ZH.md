# JapaneseASMR Downloader & Audio Player

<p align="center">
  <b>语言 / Languages:</b>
  <a href="README.md">English</a> |
  <a href="README_ID.md">Bahasa Indonesia</a> |
  <a href="README_JA.md">日本語</a> |
  <b>简体中文</b>
</p>

一款现代化的一站式桌面应用程序，用于下载 JapaneseASMR 音频、自动合并多音轨与特典、嵌入 DLsite 官方高清封面与完整元数据、支持章节标记（Chapters）与 CUE 分轨文件，并配备基于 Windows Media Foundation 的低延迟内置音频播放器。

---

## 主要功能

### 1. 现代化桌面图形界面（GUI）与多语言支持
- **全国际化支持（i18n）**: 支持简体中文、英语、日语和印尼语。默认自动跟随 Windows 系统语言，并可在设置中实时切换界面语言（无需重启应用）。
- **护眼深色主题**: 采用 Dracula / Catppuccin 优雅配色，清晰舒适。
- **实时 DLsite 元数据与高清封面预览**:
  - 完整作品标题
  - 声优阵容（多 CV 支持）
  - 社团 / 制作社名称
  - 年龄限制（全年龄 / R18）
  - 分类与官方标签
- **灵活的队列添加**: 支持通过空格或逗号批量添加多个 RJ 号（如 `RJ01673437`、`RJ278932`）、asmr.one 链接、japaneseasmr 文章链接或 DLsite 商品页面。
- **历史记录与本地库管理**: 自动记录已下载作品，包含离线封面缩略图、磁盘占用统计及播放器一键联动。

### 2. 内置音频播放器（Windows Media Foundation）
- **高性能原生音频引擎**: 采用 Windows Media Foundation（`NativeMFPlayer`），无延迟流畅播放 `.m4a`、`.mp3`、`.wav`、`.flac`、`.aac` 格式。
- **交互式章节面板**: 实时展示剧情章节与场景。双击任意章节即可直接跳转至对应时间戳，并具备当前播放章节自动高亮跟随功能。
- **子文件夹递归扫描**: 自动扫描下载目录及所有下层子目录中的音频文件，并关联对应的本地或在线封面。
- **完整播放控制**: 交互式时间轴滑动条、音量控制（0% – 100%）、单曲循环模式、上一首/下一首切换。

### 3. 高速下载引擎与双源自动回退
- **双源音频引擎**: 优先从 `japaneseasmr.com`（`weeab0o.xyz`）获取，若作品尚未收录，则自动无缝回退至 `asmr.one` 检索下载。
- **智能音轨过滤启发算法**: 自动解析 `asmr.one` 的复杂目录结构，智能筛选出正剧剧情（`本編`）与语音特典，自动跳过重复的多吉字节 WAV 格式、音效片段及环境背景音。
- **智能极速无损封装（Fast Remux）**: 对 AAC 音频直接进行无损封装（Stream Copy），耗时数秒即可生成内置章节标记的 M4A 文件，或输出带 CUE 分轨文件的 320k 高品质 MP3。
- **多层级高清封面回退**: 按照 JapaneseASMR CDN -> DLsite 官方全高清（`img.dlsite.jp`） -> asmr.one CDN 的顺序逐级获取最佳封面。
- **aria2c 多线程并行加速**: 结合 `yt-dlp` 与 `aria2c`（单个音频流最高支持 16 条并行连接），实现满速下载。
- **yt-dlp 引擎内置更新**: 支持在设置菜单中自由选择 **Stable**（稳定版）或 **Nightly**（每日构建版）进行一键更新。

### 4. 存储与偏好设置
- **自由修改下载路径**: 随时更改音频保存目录。
- **一键清理缓存**: 监控并快速清理封面缩略图缓存（`.cache/covers/`）与临时下载分段（`.cache/temp/`）。
- **文件命名偏好**: 支持选择标准 RJ 号命名或作品原标题命名。

---

## 系统要求

若从源码运行，需满足以下环境要求：

1. **Windows 10 / 11 (64位)**
2. **Python 3.8+**（推荐 Python 3.10 – 3.14）
3. **Pillow**（图像处理库）：
   ```bash
   pip install Pillow
   ```
4. **支持工具**（放置于 `bin/` 目录或添加至系统环境变量 `PATH`）：
   - **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
   - **[aria2c](https://github.com/aria2/aria2)**
   - **[ffmpeg](https://ffmpeg.org/)**

---

## 安装与使用

### 1. 使用 Windows 安装包（推荐普通用户使用）
无需安装 Python 或任何额外命令行工具：
1. 前往 **[Releases](https://github.com/SayMaven/japaneseasmr-dl/releases)** 页面下载最新安装包 **`JapaneseASMR_Setup_v1.1.1.exe`**。
2. 运行安装程序并按照向导完成安装。
3. 安装完成后即可从开始菜单或桌面快捷方式直接启动！

---

### 2. 从源码运行（开发者模式）

1. **克隆仓库**:
   ```bash
   git clone https://github.com/SayMaven/japaneseasmr-dl.git
   cd japaneseasmr-dl
   ```

2. **安装 Python 依赖**:
   ```bash
   pip install Pillow
   ```

3. **确认外部工具已就绪**:
   确保 `bin/` 目录下存在 `yt-dlp.exe`、`ffmpeg.exe` 与 `aria2c.exe`，或它们已在系统 PATH 中。

4. **启动程序**:
   * **桌面 GUI 模式（推荐）**:
     ```bash
     python main.py
     ```
   * **终端 CLI 模式**:
     ```bash
     python cli.py
     ```

---

## 开源许可证
本项目基于 **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)** 协议开源。版权所有 © 2026 **SayMaven**。

