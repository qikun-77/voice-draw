# Voice Draw — 纯语音控制绘图工具 v3.0

## Demo 视频
> 🎬 完整演示视频

演示视频地址：[https://www.bilibili.com/video/BV1hAJn68Efw/?spm_id_from=333.1387.homepage.video_card.click]

百度网盘备用：[https://pan.baidu.com/pfile/video?path=%2Fvoicedraw%2Fvoice%20draw%20demo%E8%A7%86%E9%A2%91.mp4&theme=light&view_from=personal_file&from=home]

仅通过语音指令完成绘图创作。**点击开始录音，说完再点击停止**，无需键盘输入。

## 快速开始

### 最快方式：一键启动

双击 **`一键启动.bat`**，自动检查依赖 → 提示输入 API Key → 启动服务 → 打开浏览器。

### 手动启动

```bash
cd voice-draw
pip install -r requirements.txt

# API Key 可通过环境变量设置，或直接修改 server.py 第18行
set DEEPSEEK_API_KEY=sk-your-key    # Windows
python server.py                     # 启动服务
```

浏览器访问 **http://localhost:8765**

> ⚠️ 必须通过 `http://localhost:8765` 访问，不要直接双击打开 index.html。

## 交互方式

| 操作 | 方式 |
|------|------|
| 🎤 **点击按钮** | 点击开始 → 说话 → 再点击停止 |
| ⌨️ **空格键** | 按空格切换录音 |
| 📥 **Ctrl+S** | 导出 PNG |
| ↩️ **Ctrl+Z** | 撤销 |
| 🗑 **Delete** | 清空画布 |
| ❓ **?** | 显示快捷键面板 |

## 支持的指令

### 基本图形（本地引擎，零 API 消耗）

| 类别 | 示例指令 |
|------|---------|
| 圆形 | "画红色圆"、"画圆圈" |
| 矩形 | "画蓝色方块"、"长方形" |
| 线段 | "画一条线" |
| 三角形 | "画三角" |
| ⭐ 五角星 | "画五角星"、"画星星" |
| ❤️ 心形 | "画爱心"、"画心形" |
| 💎 菱形 | "画菱形"、"画钻石" |
| ⬡ 五边形 | "画五边形" |
| ⬡ 六边形 | "画六边形" |
| ➡ 箭头 | "画箭头" |
| ✚ 十字 | "画十字" |

### 复合图形（本地引擎）

| 指令 | 效果 |
|------|------|
| "画太阳" | 黄圆 + 8条光芒线 |
| "画一朵云" | 4个重叠灰圆 |
| "画房子" | 矩形 + 三角屋顶 + 门 |
| "画一棵树" | 矩形树干 + 圆形树冠 |

### 复杂角色（LLM 自动分解，~¥0.003/次）

奥特曼、钢铁侠、小黄人、皮卡丘、哆啦A梦、龙、火箭、城堡、机器人

### 文字（中英文/数字/符号）

"写Hello World"、"写你好"、"写12345"、"写!@#$"

### 编辑操作

"把圆变成绿色"（API）/"删除方块"（本地）/"清空画布"（本地）/"撤销"（本地）

## 混合模式

| 模式 | 占比 | API 消耗 |
|------|------|----------|
| 🟢 **本地规则引擎** | ~85% | **0** |
| 🔵 **DeepSeek API** | ~15% | ¥0.003/次 |

操作日志会显示来源标签：<span style="background:#10b98122;color:#10b981;padding:1px 6px;border-radius:3px;font-size:.65em;font-weight:700">本地</span> / <span style="background:#6366f122;color:#6366f1;padding:1px 6px;border-radius:3px;font-size:.65em;font-weight:700">API</span>

## v3.0 新特性

| 特性 | 说明 |
|------|------|
| 🎨 深色网格画布 | Figma 风格，白描边 + 半透明填充 |
| 🌌 动态光晕背景 | 三色径向渐变呼吸动画 |
| 🎵 真实音频波形 | Web Audio API 麦克风实时驱动 7 柱跳动 |
| ✨ 弹性入场动画 | 图形 scale(0)→(1.15)→(1) 弹出 |
| ⏳ AI 思考动画 | 等待 API 时按钮紫色流光 |
| 🔔 Toast 通知 | 右上角滑入，3 秒消失 |
| 📥 PNG 导出 | 右上角按钮 / Ctrl+S |
| ⌨️ 快捷键面板 | 按 ? 弹出全键盘指南 |
| 📋 图层列表 | 侧栏底部实时显示所有对象 |
| 💡 Hover 高亮 | 鼠标悬停图形发光 |

## 项目结构

```
voice-draw/
├── 一键启动.bat          ← 双击运行
├── server.py             # FastAPI + 本地引擎 + DeepSeek API
├── index.html            # 前端 v3.0：深色画布 + 波形 + 导出 + 图层
├── DESIGN_DOC.md         # 设计文档（能力矩阵、局限分析）
├── PR_RECORD.md          # PR 提交记录（6个独立PR）
├── requirements.txt      # Python 依赖
└── README.md             # 本文件
```

## PR 提交结构

| PR | 标题 |
|----|------|
| PR1 | 初始化项目骨架 — 基础 API + SVG 画布 |
| PR2 | 混合模式本地引擎 — 85%+ 指令零 API |
| PR3 | UI 全面升级 — 毛玻璃、深色画布、Toast |
| PR4 | 8+ 新形状 — 五角星/爱心/菱形/多边形/箭头/十字 |
| PR5 | 复杂角色分解 + 中英文文字 |
| PR6 | 交互增强 — 波形、动画、导出、快捷键、图层列表 |

详见 `PR_RECORD.md`


## 浏览器要求

- **Chrome 或 Edge**（需支持 Web Speech API + Web Audio API）
- 首次使用需允许麦克风权限
