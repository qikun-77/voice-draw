# PR 提交记录 — Voice Draw 纯语音控制绘图工具

## PR1: 初始化项目骨架

- **标题**: feat: 初始化项目骨架 — 基础语音绘图 API + SVG 画布前端
- **功能描述**: 
  - FastAPI 后端 `/api/parse` 端点接收绘图指令返回 JSON 操作序列
  - 前端 SVG 800×600 画布 + Web Speech API 语音识别
  - 支持 circle/rect/line/triangle/text 五种基本图形的渲染
  - 前端直接打开 index.html 即可使用（CORS 已配置）
- **实现思路**: 
  - 后端使用 FastAPI + DeepSeek Chat API，System Prompt 定义操作类型/颜色/空间布局规则
  - 前端 SVG DOM 直接操作，每个图形独立元素 + data-id 标识
  - 语音识别使用浏览器内置 Web Speech API (continuous=true 持续收音)
- **测试方式**: 
  1. `pip install -r requirements.txt && python server.py`
  2. 浏览器打开 `http://localhost:8765`
  3. 点击录音按钮说"画一个红色的圆"→ 画布出现红色圆形
  4. 点击快捷按钮"太阳"验证复合图形
- **依赖**: fastapi, uvicorn, openai

---

## PR2: 添加混合模式本地规则引擎

- **标题**: feat: 添加本地规则引擎，85%+ 指令零 API 消耗
- **功能描述**:
  - 新增 `local_parse()` 函数，用正则+关键词匹配处理常见简单指令
  - 支持：基本图形（圆/矩形/线/三角形）+ 颜色属性 + 清空/撤销
  - 响应增加 `source` 字段区分 `local`/`api`
  - 前端日志显示来源标签（本地/API）
- **实现思路**:
  - 在 `/api/parse` 端点内先调 `local_parse()`，匹配成功直接返回
  - 匹配规则：清空/撤销用 `re.fullmatch`、图形用正则提取颜色+形状+位置
  - 未匹配指令降级调用 DeepSeek API
  - 颜色映射表 COLOR_MAP 支持红/蓝/绿/黄/黑/白/橙/紫 8色
- **测试方式**:
  1. 说"画一个红色的圆"→ 日志显示「本地」标签，画布出现红色圆（不消耗API）
  2. 说"清空画布"→ 画布清空（本地）
  3. 说"在左边画太阳右边画白云"→ 日志显示「API」标签（复杂指令降级）
  4. 检查后端日志确认 local/api 来源

---

## PR3: UI 全面升级 — iOS/Gemini 质感

- **标题**: feat: UI 全面升级 — 毛玻璃面板、动态背景、深色画布网格、Toast 通知
- **功能描述**:
  - 毛玻璃面板（backdrop-filter: blur(40px) saturate(160%)）
  - 动态光晕背景（三色径向渐变 + 20s 呼吸动画）
  - 深色网格画布（#12121a 底 + 20px 网格线）
  - Inter 字体（SF Pro 风格）
  - Toast 通知系统（右上角滑入，3秒自动消失）
  - 录音脉冲动画 + 波形跳动
  - 侧栏加宽至 400px
- **实现思路**:
  - 纯 CSS 实现毛玻璃和动态背景，零依赖
  - Toast 用 DOM 动态创建 + CSS animation（toastIn/toastOut）
  - 画布叠加网格层 `.canvas-grid-bg` 用 linear-gradient 实现
  - 音频波形降级方案：Web Audio API 不可用时用随机动画
- **测试方式**:
  1. 刷新页面 → 看到动态光晕背景 + 深色画布 + 毛玻璃面板
  2. 画一个图形 → 右上角出现绿色 Toast "绘制完成 (local)"
  3. 故意断开后端 → Toast 提示"失败"
  4. 说指令后观察侧栏日志卡片样式

---

## PR4: 新增 8+ 形状支持 — 五角星/心形/菱形/多边形/箭头/十字

- **标题**: feat: 新增 8 种形状 — 五角星、心形、菱形、五/六边形、箭头、十字
- **功能描述**:
  - 本地引擎新增形状生成器：`make_star`, `make_heart`, `make_diamond`, `make_pentagon`, `make_hexagon`, `make_arrow`, `make_cross`
  - 前端渲染引擎新增 `polygon` 类型支持（SVG `<polygon>` 元素）
  - 所有新形状零 API 消耗，本地生成坐标
  - 快捷按钮面板新增：⭐五角星 ❤️爱心 💎菱形 ⬡六边形 ➡箭头
- **实现思路**:
  - 五角星：10 个顶点用三角函数计算内外半径交替
  - 心形：多边形近似，7 个控制点
  - 正多边形：等角度分布顶点
  - 箭头：线段 + 两个短线段构成三角形箭头
  - 十字：两条垂直线段
- **测试方式**:
  1. 点击快捷按钮"⭐五角星"→ 画布出现金色五角星（本地）
  2. 说"画红色爱心"→ ❤️ 出现（本地）
  3. 说"画菱形"→ 💎 出现（本地）
  4. 说"画六边形"→ 绿色六边形（本地）
  5. 说"画箭头"→ 箭头出现（本地）

---

## PR5: 复杂角色分解 + 中英文文字支持

- **标题**: feat: 复杂角色几何分解（奥特曼/钢铁侠等9种）+ 中英文写字
- **功能描述**:
  - System Prompt 强化：内置 9 种角色/物体分解模板
  - 支持：奥特曼、钢铁侠、小黄人、皮卡丘、哆啦A梦、龙、火箭、城堡、机器人
  - 文字支持中英混排、数字、特殊符号（`!@#$%`）
  - 颜色扩充至 15 色（新增金/银/青/天蓝/深蓝/浅绿/深红/浅粉/米色）
- **实现思路**:
  - LLM System Prompt 中明确写死各角色的几何分解方案（坐标+颜色）
  - 写字本地引擎支持：`re.search` 匹配"写/打字/文字/文本" + 内容提取
  - 字体大小支持"大"/"小"修饰词
- **测试方式**:
  1. 说"画奥特曼"→ 银色头+红色身体+黄色眼睛+四肢（API调用）
  2. 说"画钢铁侠"→ 红金配色角色
  3. 说"写Hello World"→ 画布显示黑色英文（本地）
  4. 说"写你好世界"→ 画布显示中文（本地）

---

## PR6: 交互增强 — 真实音频波形、弹性动画、导出PNG、快捷键面板、图层列表

- **标题**: feat: 交互增强 — 真实波形、弹性动画、PNG导出、快捷键面板、图层列表
- **功能描述**:
  - 真实音频波形：Web Audio API 接入麦克风，7柱实时随音量跳动
  - 弹性入场动画：新图形 scale(0)→scale(1.15)→scale(1)
  - PNG 导出：右上角按钮 / Ctrl+S，SVG→Canvas→PNG
  - 快捷键面板：按 `?` 弹出，含 6 组快捷键（空格/Ctrl+Z/Delete/Ctrl+S/?/Esc）
  - 图层列表：侧栏底部实时显示所有对象，可点击定位高亮
  - Hover 高亮：鼠标悬停图形发光
  - AI 思考动画：等待 API 时按钮流光 + "✨ AI 正在绘制…"
- **实现思路**:
  - Web Audio API: `getUserMedia` → `AnalyserNode` → `getByteFrequencyData` → CSS height
  - 弹入动画：CSS `@keyframes popIn` + `.shape-animate` class
  - PNG 导出：SVG 序列化 → Image → Canvas → toDataURL → download
  - 图层列表：遍历 `objects` 生成 DOM，点击触发 `selectObject` 高亮
- **测试方式**:
  1. 录音 → 观察波形柱随声音跳动
  2. 画图形 → 观察弹性缩放弹出
  3. 点击 📥 / Ctrl+S → 下载 voice-draw.png
  4. 按 `?` → 快捷键面板弹出
  5. 画多个图形 → 侧栏底部出现图层列表