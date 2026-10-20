[English](README.md) | **简体中文**

# Turbo Photo Sorter（极速照片筛选器）

适用于 Windows 的快速、键盘驱动的照片筛选工具。逐张翻看文件夹里的照片，把每张标记为**保留**、**丢弃**或**待定**，可快速调整亮度和对比度，整理好的副本会放进子文件夹。你的原始文件永远不会被改动。

[![Release](https://img.shields.io/github/v/release/Kylekk29/ImageSorter)](https://github.com/Kylekk29/ImageSorter/releases/latest)

## 下载

从[最新发布](https://github.com/Kylekk29/ImageSorter/releases/latest)下载 `TurboPhotoSorter-1.0.0-x64-Portable.exe`。它是单个文件，无需安装。由于程序没有代码签名，Windows SmartScreen 可能会提示警告：请选择**更多信息 → 仍要运行**。

## 功能

- 三选一分类，支持撤销（`Ctrl+Z`）
- 后台加载和缩略图胶片条，浏览不卡顿
- 非破坏性的亮度和对比度调整、缩放和平移、全屏
- EXIF 信息面板（相机、镜头、曝光）
- 深色和浅色主题
- 进度按文件夹保存，退出后可继续，不必重新筛选

## 键盘快捷键

| 按键 | 操作 |
|---|---|
| `→` / `K` / `Space` | 保留 |
| `↓` / `N` | 丢弃 |
| `M` | 待定 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+O` | 打开文件夹 |
| `F11` | 全屏（`Esc` 退出） |
| `+` / `-` / `0` | 放大 / 缩小 / 重置 |
| 鼠标滚轮 | 缩放 |
| 中键或右键拖动 | 平移 |

## 输出

筛选时会把文件复制到你的源文件夹中：

```
YourPhotos/
├── Keep/  Discard/  Maybe/                      # 原图的副本
├── Keep_Modified/  Discard_Modified/  Maybe_Modified/   # 已应用你调整的副本
└── turbo_sorter_log.json                        # 记录哪些文件已处理（用于继续）
```

## 从源码运行

需要 Python 3.10+ 和 Tkinter（Windows 标准安装包已包含）。

```bash
pip install -r requirements.txt
python main.py
```

`requirements.txt` 里还列出了 PyInstaller，只有构建 exe 时才需要。

## 构建 exe

```bash
pyinstaller --name TurboPhotoSorter --windowed --onefile --exclude-module PySide6 main.py
```

## 许可证

MIT，见 [LICENSE](LICENSE)。
