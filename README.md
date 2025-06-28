## JNU-EXAM-Downloader

This is the downloader for my other project [JNU-EXAM](https://github.com/gubaiovo/JNU-EXAM).

## How to use

``` bash
uv sync
nuitka --standalone --onefile --enable-plugin=pyqt6 --windows-console-mode=disable --windows-icon-from-ico=.\logo.ico .\main.py
```