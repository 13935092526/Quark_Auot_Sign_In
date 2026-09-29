"""字体发现与加载：优先使用系统中文字体，兼容 Windows / macOS / Linux。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import ImageFont

# 常见字体族关键字 -> 候选字体文件名（按顺序尝试）
FONT_FAMILIES: dict[str, list[str]] = {
    "yahei":  ["msyh.ttc", "msyhbd.ttc", "Microsoft YaHei", "PingFang"],
    "hei":    ["simhei.ttf", "SimHei", "NotoSansCJK"],
    "song":   ["simsun.ttc", "SimSun", "NotoSerifCJK"],
    "kai":    ["simkai.ttf", "KaiTi", "STKaiti"],
    "deng":   ["Deng.ttf", "Dengxian"],
    "mono":   ["consola.ttf", "CascadiaMono", "DejaVuSansMono"],
    "arial":  ["arial.ttf", "Helvetica"],
}

_BOLD_OVERRIDES = {
    "yahei": "msyhbd.ttc",
    "hei":   "simhei.ttf",
    "song":  "simsun.ttc",
    "deng":  "Dengb.ttf",
    "mono":  "consolab.ttf",
    "arial": "arialbd.ttf",
}

# 字体搜索目录
_FONT_DIRS: list[Path] = []
if sys.platform == "win32":
    _FONT_DIRS.append(Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts")
else:
    _FONT_DIRS.extend(
        Path(p) for p in ("/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"))
    )
    if sys.platform == "darwin":
        _FONT_DIRS.append(Path("/System/Library/Fonts"))
        _FONT_DIRS.append(Path("/Library/Fonts"))

# 兜底顺序：雅黑 -> 黑体 -> 宋体 -> Noto CJK
_FALLBACKS = ["msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc", "PingFang", "NotoSansCJK"]

_cache: dict[tuple[str | None, int], ImageFont.FreeTypeFont] = {}


def _match(candidate: str) -> Path | None:
    """在字体目录中查找候选字体（支持子串匹配，忽略大小写）。"""
    cand = candidate.lower()
    for d in _FONT_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and cand in f.name.lower():
                return f
    return None


def find_font(family: str | None = None, bold: bool = False) -> str | None:
    """返回字体文件绝对路径；family 可为关键字、字体名或完整路径。"""
    if family:
        p = Path(family)
        if p.is_file():
            return str(p)
        key = family.lower()
        if key in FONT_FAMILIES:
            names = ([_BOLD_OVERRIDES[key]] if bold and key in _BOLD_OVERRIDES else []) + FONT_FAMILIES[key]
            for n in names:
                hit = _match(n)
                if hit:
                    return str(hit)
        hit = _match(family)
        if hit:
            return str(hit)
    for n in _FALLBACKS:
        hit = _match(n)
        if hit:
            return str(hit)
    return None


def load_font(size: int, family: str | None = None, bold: bool = False) -> ImageFont.FreeTypeFont:
    """加载指定字号的字体（带缓存）。找不到系统字体时退回 PIL 默认字体。"""
    path = find_font(family, bold)
    key = (path, size)
    if key not in _cache:
        if path:
            _cache[key] = ImageFont.truetype(path, size)
        else:
            _cache[key] = ImageFont.load_default(size)
    return _cache[key]
