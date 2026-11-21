[English](README.md) | **简体中文**

# Turbo Photo Sorter（极速照片筛选器）

Turbo Photo Sorter 是一款开源的 Windows 照片筛选工具。使用键盘把照片标为**保留**、**丢弃**或**待定**。程序会把副本放进相应的子文件夹，原始照片保持不变。

## 下载 Windows x64 版

下载 [TurboPhotoSorter-1.1.0-x64-Portable.exe](https://github.com/Kylekk29/ImageSorter/releases/download/v1.1.0/TurboPhotoSorter-1.1.0-x64-Portable.exe)，双击即可运行，无需安装。

程序未签名，Windows SmartScreen 可能会显示提示。[发布页面](https://github.com/Kylekk29/ImageSorter/releases/latest)提供 SHA-256 校验值。

## 筛选照片

1. 把一个文件夹或同一文件夹内选中的照片拖到预览区。也可以按 `Ctrl+O` 打开文件夹。
2. 按 `K` 保留、`N` 丢弃或 `M` 标为待定。保存成功后，程序会跳到下一张未分类的照片。
3. 按 `[`、`]` 或点击缩略图浏览。按 `Ctrl+Z` 可撤销本次会话中的上一次分类，并移除该操作生成的副本。

程序支持 JPEG、PNG、TIFF、WebP 和 BMP。浏览时按需加载缩略图。侧栏可调整亮度和对比度、查看 EXIF 信息，并切换深色或浅色主题。

| 快捷键 | 操作 |
| --- | --- |
| `K`、`→` 或 `Space` | 保留 |
| `N` 或 `↓` | 丢弃 |
| `M` | 待定 |
| `[` / `]` | 浏览上一张或下一张 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+O` | 打开文件夹 |
| `F11` / `Esc` | 进入或退出全屏 |
| 鼠标滚轮或 `+` / `-` | 缩放 |
| `0` | 重置缩放 |
| 鼠标中键或右键拖动 | 平移缩放后的预览 |

## 文件保存位置

分类结果保存在原始照片所在的文件夹中。

- `Keep/`、`Discard/` 和 `Maybe/` 保存原图副本。
- `Keep_Modified/`、`Discard_Modified/` 和 `Maybe_Modified/` 保存应用亮度和对比度调整后的原分辨率副本。
- `turbo_sorter_log.json` 记录已分类的照片。重新打开文件夹后可继续筛选。

所需副本保存成功后才会更新进度。目标位置有同名文件时，程序会提示冲突，并保留现有文件。

## 从源码运行或构建

需要 Python 3.10 或更新版本，以及 Tkinter。构建 Windows x64 版时，请在 Windows 上使用 x86 64 位 Python。

```powershell
python -m pip install -r requirements.txt
python main.py
```

在 PowerShell 中运行以下命令，便携版会生成在 `dist/` 中。

```powershell
.\build.ps1
```

运行 `python -m unittest discover -s tests -v` 可执行回归测试。

## 开源许可

本项目的源代码采用 [MIT 许可证](LICENSE)。便携版内含项目许可证及随附依赖的许可声明。
