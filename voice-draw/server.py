"""
Voice Draw — 纯语音控制绘图工具
FastAPI + 混合模式：本地规则引擎(80%+指令) + DeepSeek API(复杂指令)
"""
import json, os, re, math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import uvicorn

app = FastAPI(title="Voice Draw API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-c0fb6eab863c4854bbfe45270ae24d68")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

_id_counter = 0
def next_id(prefix="obj"):
    global _id_counter; _id_counter += 1; return f"{prefix}_{_id_counter}"

# =====================================================
# 颜色映射 (扩充)
# =====================================================
COLOR_MAP = {
    "红色":"#FF0000","红的":"#FF0000","蓝色":"#0000FF","蓝的":"#0000FF",
    "绿色":"#00FF00","绿的":"#00FF00","黄色":"#FFFF00","黄的":"#FFFF00",
    "黑色":"#000000","黑的":"#000000","白色":"#FFFFFF","白的":"#FFFFFF",
    "橙色":"#FF8800","橘色":"#FF8800","紫色":"#8800FF","紫的":"#8800FF",
    "粉色":"#FF69B4","粉的":"#FF69B4","灰色":"#888888","灰的":"#888888",
    "棕色":"#8B4513","褐色":"#8B4513","褐的":"#8B4513",
    "金色":"#FFD700","银色":"#C0C0C0","青色":"#00FFFF","青色":"#00FFFF",
    "skin":"#FFD5B4","skin":"#FFD5B4",
    "天蓝":"#87CEEB","深蓝":"#000080","浅绿":"#90EE90","深绿":"#006400",
    "深红":"#8B0000","浅粉":"#FFB6C1","米色":"#F5F5DC","棕色":"#8B4513",
}

def extract_color(text: str) -> str | None:
    for name, hex_val in COLOR_MAP.items():
        if name in text: return hex_val
    return None

# =====================================================
# 新形状生成器
# =====================================================
def make_star(cx, cy, r, fill=None, stroke="#000000", sw=2):
    """五角星"""
    pts = []
    for i in range(10):
        angle = math.pi/2 + i * math.pi/5
        rr = r if i % 2 == 0 else r * 0.38
        pts.append(f"{cx+rr*math.cos(angle)},{cy-rr*math.sin(angle)}")
    return {"id":next_id("star"),"type":"polygon","params":{"points":" ".join(pts),"fill":fill or "#FFD700","stroke":stroke,"strokeWidth":sw}}

def make_heart(cx, cy, size, fill=None, stroke="#000000", sw=2):
    """心形 (两个圆+三角形)"""
    px = f"{cx},{cy+size*0.35} {cx-size},{cy-size*0.3} {cx-size*0.5},{cy-size*0.8} {cx},{cy-size*0.1} {cx+size*0.5},{cy-size*0.8} {cx+size},{cy-size*0.3}"
    return {"id":next_id("heart"),"type":"polygon","params":{"points":px,"fill":fill or "#FF0000","stroke":stroke,"strokeWidth":sw}}

def make_diamond(cx, cy, w, h, fill=None, stroke="#000000", sw=2):
    """菱形"""
    pts = f"{cx},{cy-h} {cx+w},{cy} {cx},{cy+h} {cx-w},{cy}"
    return {"id":next_id("diamond"),"type":"polygon","params":{"points":pts,"fill":fill or "#00FFFF","stroke":stroke,"strokeWidth":sw}}

def make_pentagon(cx, cy, r, fill=None, stroke="#000000", sw=2):
    """正五边形"""
    pts = []
    for i in range(5):
        angle = -math.pi/2 + i * 2*math.pi/5
        pts.append(f"{cx+r*math.cos(angle)},{cy+r*math.sin(angle)}")
    return {"id":next_id("pent"),"type":"polygon","params":{"points":" ".join(pts),"fill":fill or "#8800FF","stroke":stroke,"strokeWidth":sw}}

def make_hexagon(cx, cy, r, fill=None, stroke="#000000", sw=2):
    """正六边形"""
    pts = []
    for i in range(6):
        angle = i * 2*math.pi/6
        pts.append(f"{cx+r*math.cos(angle)},{cy+r*math.sin(angle)}")
    return {"id":next_id("hex"),"type":"polygon","params":{"points":" ".join(pts),"fill":fill or "#00AA00","stroke":stroke,"strokeWidth":sw}}

def make_arrow(x1, y1, x2, y2, color="#000000", sw=2):
    """箭头 (线段+三角形箭头)"""
    dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy) or 1
    ux, uy = dx/L, dy/L
    line_action = {"id":next_id("arr_l"),"type":"line","params":{"x1":x1,"y1":y1,"x2":x2,"y2":y2,"stroke":color,"strokeWidth":sw}}
    head1 = {"id":next_id("arr_h1"),"type":"line","params":{"x1":x2,"y1":y2,"x2":round(x2-15*ux-8*uy),"y2":round(y2-15*uy+8*ux),"stroke":color,"strokeWidth":sw+1}}
    head2 = {"id":next_id("arr_h2"),"type":"line","params":{"x1":x2,"y1":y2,"x2":round(x2-15*ux+8*uy),"y2":round(y2-15*uy-8*ux),"stroke":color,"strokeWidth":sw+1}}
    return [line_action, head1, head2]

def make_cross(cx, cy, size, color="#000000", sw=2):
    """十字"""
    return [
        {"id":next_id("cross_h"),"type":"line","params":{"x1":cx-size,"y1":cy,"x2":cx+size,"y2":cy,"stroke":color,"strokeWidth":sw}},
        {"id":next_id("cross_v"),"type":"line","params":{"x1":cx,"y1":cy-size,"x2":cx,"y2":cy+size,"stroke":color,"strokeWidth":sw}},
    ]

# =====================================================
# 本地规则引擎 (扩充版)
# =====================================================
def local_parse(instruction: str, history: list[dict]) -> dict | None:
    text = instruction.strip()
    hi = history  # shorthand

    # ── 清空 / 撤销 ──
    if re.fullmatch(r"(清空|全部删除|重来|清除|全清)", text):
        return {"intent":"clear","actions":[{"id":next_id("clr"),"type":"clear","params":{}}],"clarification":None,"source":"local"}
    if re.fullmatch(r"撤销", text):
        return {"intent":"undo","actions":[{"id":next_id("undo"),"type":"undo","params":{}}],"clarification":None,"source":"local"}

    # ── 新形状：五角星 ──
    if re.search(r"(五角星|星星|星形)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#FFD700"
        cx, cy = parse_position(text, "star")
        r = 80 if "大" in text else (35 if "小" in text else 60)
        return {"intent":"draw","actions":[make_star(cx,cy,r,fill=color)],"clarification":None,"source":"local"}

    # ── 新形状：心形 ──
    if re.search(r"(心形|爱心|心|桃心)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它|中心", text):
        color = extract_color(text) or "#FF0000"
        cx, cy = parse_position(text, "heart")
        size = 70 if "大" in text else (30 if "小" in text else 50)
        return {"intent":"draw","actions":[make_heart(cx,cy,size,fill=color)],"clarification":None,"source":"local"}

    # ── 新形状：菱形 ──
    if re.search(r"(菱形|钻石)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#00FFFF"
        cx, cy = parse_position(text, "diamond")
        w = 90 if "大" in text else (40 if "小" in text else 60)
        h = 135 if "大" in text else (60 if "小" in text else 90)
        return {"intent":"draw","actions":[make_diamond(cx,cy,w,h,fill=color)],"clarification":None,"source":"local"}

    # ── 新形状：五边形 ──
    if re.search(r"(五边形|五边)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#8800FF"
        cx, cy = parse_position(text, "pentagon")
        r = 80 if "大" in text else (35 if "小" in text else 60)
        return {"intent":"draw","actions":[make_pentagon(cx,cy,r,fill=color)],"clarification":None,"source":"local"}

    # ── 新形状：六边形 ──
    if re.search(r"(六边形|六边)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#00AA00"
        cx, cy = parse_position(text, "hexagon")
        r = 80 if "大" in text else (35 if "小" in text else 60)
        return {"intent":"draw","actions":[make_hexagon(cx,cy,r,fill=color)],"clarification":None,"source":"local"}

    # ── 新形状：箭头 ──
    if re.search(r"(箭头)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#000000"
        cx, cy = parse_position(text, "arrow")
        x1, y1 = cx-175, cy
        x2, y2 = cx+175, cy
        return {"intent":"draw","actions":make_arrow(x1,y1,x2,y2,color=color),"clarification":None,"source":"local"}

    # ── 新形状：十字 ──
    if re.search(r"(十字|交叉)", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#000000"
        cx, cy = parse_position(text, "cross")
        size = 60 if "大" in text else (25 if "小" in text else 40)
        return {"intent":"draw","actions":make_cross(cx,cy,size,color=color),"clarification":None,"source":"local"}

    # ── 太阳 ──
    if re.search(r"太阳", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color = extract_color(text) or "#FFFF00"; r=50; cx,cy=680,100
        actions=[{"id":next_id("sun"),"type":"circle","params":{"cx":cx,"cy":cy,"r":r,"fill":color,"stroke":color,"strokeWidth":2}}]
        for a in range(0,360,45):
            rad=math.radians(a)
            actions.append({"id":next_id("ray"),"type":"line","params":{"x1":round(cx+(r+5)*math.cos(rad)),"y1":round(cy+(r+5)*math.sin(rad)),"x2":round(cx+(r+20)*math.cos(rad)),"y2":round(cy+(r+20)*math.sin(rad)),"stroke":color,"strokeWidth":3}})
        return {"intent":"draw","actions":actions,"clarification":None,"source":"local"}

    # ── 云 ──
    if re.search(r"云", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        color=extract_color(text) or "#DDDDDD"; bx,by=150,120
        actions=[{"id":next_id("cloud"),"type":"circle","params":{"cx":bx+dx,"cy":by+dy,"r":30,"fill":color,"stroke":"#CCCCCC","strokeWidth":1}} for dx,dy in [(0,0),(35,-15),(65,5),(30,15)]]
        return {"intent":"draw","actions":actions,"clarification":None,"source":"local"}

    # ── 房子 ──
    if re.search(r"房子", text) and not re.search(r"变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        cb=extract_color(text) or "#8B4513"
        actions=[
            {"id":next_id("house_body"),"type":"rect","params":{"x":300,"y":280,"width":120,"height":100,"fill":cb,"stroke":"#000","strokeWidth":2}},
            {"id":next_id("house_roof"),"type":"triangle","params":{"x1":280,"y1":280,"x2":420,"y2":280,"x3":360,"y3":200,"fill":"#CC0000","stroke":"#000","strokeWidth":2}},
            {"id":next_id("house_door"),"type":"rect","params":{"x":345,"y":320,"width":30,"height":60,"fill":"#663300","stroke":"#000","strokeWidth":1}},
        ]
        return {"intent":"draw","actions":actions,"clarification":None,"source":"local"}

    # ── 树 ──
    if re.search(r"树", text) and not re.search(r"云|太阳|房子|变成|改|挪|移动|删除|去掉|变大|变小|那|它", text):
        cc=extract_color(text) or "#00AA00"
        actions=[
            {"id":next_id("tree_trunk"),"type":"rect","params":{"x":470,"y":350,"width":20,"height":80,"fill":"#8B4513","stroke":"#000","strokeWidth":1}},
            {"id":next_id("tree_crown"),"type":"circle","params":{"cx":480,"cy":320,"r":50,"fill":cc,"stroke":"#000","strokeWidth":1}},
        ]
        return {"intent":"draw","actions":actions,"clarification":None,"source":"local"}

    # ── 删除 ──
    m=re.match(r"(删除|去掉|删掉|移除|擦掉)\s*(那个|这|那)?\s*(.+)", text)
    if m:
        tid=find_target(m.group(3).strip(), hi)
        if tid: return {"intent":"delete","actions":[{"id":next_id("del"),"type":"delete","params":{"targetId":tid}}],"clarification":None,"source":"local"}
        return None

    # ── 本地移动指令 ──
    # 模式: "把XX移到YY" / "把XX往ZZ移动" / "把XX挪到YY"
    move_pat = re.match(r"把\s*(那个|这|那)?\s*(.+?)\s*(移到|移动到|挪到|搬到|移|挪|搬)\s*(.+)", text)
    if move_pat:
        target_desc = move_pat.group(2).strip()
        dest_desc = move_pat.group(4).strip()
        tid = find_target(target_desc, hi)
        if tid:
            # 尝试绝对位置移动
            abs_pos = parse_position(dest_desc)
            if abs_pos != (400, 300):  # 有明确方位
                cx, cy = abs_pos
                return {"intent":"move","actions":[{"id":next_id("mv"),"type":"move","params":{"targetId":tid,"x":cx,"y":cy}}],"clarification":None,"source":"local"}
            # 尝试相对位移
            delta = parse_move_delta(dest_desc)
            if delta:
                dx, dy = delta
                return {"intent":"move","actions":[{"id":next_id("mv"),"type":"move","params":{"targetId":tid,"dx":dx,"dy":dy}}],"clarification":None,"source":"local"}

    # ── 修改/移动（复杂指代）→ API ──
    if re.match(r"把\s*(那个|这|那)?\s*(.+?)\s*(变|改|成).*", text): return None
    if re.search(r"(移动|挪|搬)", text): return None

    # ── 基本形状 ──
    sr = parse_simple_shape(text); 
    if sr: return sr

    # ── 写字 ──
    m_text = re.search(r"(写|打字|文字|文本)\s*[：:""\u2018\u201c']?\s*(.+?)\s*[\u2019\u201d""]?\s*$", text)
    if m_text:
        content = m_text.group(2).strip().rstrip("。，！？.!?")
        color = extract_color(text) or "#000000"
        fs = 24
        if "大" in text: fs=40
        elif "小" in text: fs=14
        cx, cy = parse_position(text, "text")
        x, y = cx - len(content)*fs*0.3, cy
        return {"intent":"draw","actions":[{"id":next_id("txt"),"type":"text","params":{"x":x,"y":y,"content":content,"fontSize":fs,"fill":color}}],"clarification":None,"source":"local"}

    # ── 闲聊过滤 ──
    if re.search(r"(天气|笑话|吃饭|电影|音乐|播放|打开|关闭|搜索|百度|谷歌|你好|几岁|名字|你是谁)", text):
        return {"intent":"chat","actions":[],"clarification":"这是语音绘图工具，请说绘图相关指令，如「画一个红色爱心」、「写Hello World」","source":"local"}

    # ── 模糊指令 ──
    if re.match(r"^画(个|一个)?$", text) or re.match(r"^画个?东西$", text):
        return {"intent":"clarify","actions":[],"clarification":"请问您想画什么？可以说「画个五角星」、「画爱心」、「写Hello World」","source":"local"}

    return None  # 交给 API

def find_target(desc: str, history: list[dict]) -> str | None:
    if not history: return None
    dl=desc.lower()
    type_keys={"圆":"circle","圈":"circle","矩形":"rect","方块":"rect","长方形":"rect","正方形":"rect","三角":"triangle","线":"line","字":"text","文字":"text","文本":"text","星":"none","五角星":"none","爱心":"none","心形":"none","菱形":"none","五边形":"none","六边形":"none","箭头":"none","十字":"none"}
    for kw, typ in type_keys.items():
        if kw in dl:
            if typ=="none":
                for o in history:
                    if kw in o.get("id",""): return o["id"]
            else:
                cand=[o for o in history if o.get("type")==typ]
                if cand: return cand[-1]["id"]
    for cn, ch in COLOR_MAP.items():
        if cn in dl:
            for o in history:
                p=o.get("params",{})
                if p.get("fill")==ch or p.get("stroke")==ch: return o["id"]
    return None

def parse_simple_shape(text: str) -> dict | None:
    color=extract_color(text); sc=color if color else "#000000"; fc=color if color else "transparent"; sw=2
    if "粗" in text: sw=5
    elif "细" in text: sw=1
    st=None; p={}
    if re.search(r"(圆圈|圆形|个?圆|个?圈)", text):
        st="circle"; p={"cx":400,"cy":300,"r":60,"stroke":sc,"strokeWidth":sw,"fill":fc}
        if "大" in text: p["r"]=100
        elif "小" in text: p["r"]=30
        adjust_pos(p,text,"circle")
    elif re.search(r"(矩形|方块|长方形|正方形|方框|框框)", text):
        st="rect"; p={"x":300,"y":200,"width":120,"height":90,"stroke":sc,"strokeWidth":sw,"fill":fc}
        if "大" in text: p["width"],p["height"]=200,150
        elif "小" in text: p["width"],p["height"]=60,45
        adjust_pos(p,text,"rect")
    elif re.search(r"(线段|直线|一条?线|线条)", text):
        st="line"; p={"x1":200,"y1":300,"x2":600,"y2":300,"stroke":sc,"strokeWidth":sw}
    elif re.search(r"(三角)", text):
        st="triangle"
        cx, cy = parse_position(text, "triangle")
        # 默认正三角
        p={"x1":cx,"y1":cy-75,"x2":cx+80,"y2":cy+75,"x3":cx-80,"y3":cy+75,"stroke":sc,"strokeWidth":sw,"fill":fc}
        if "大" in text: p["x1"],p["y1"],p["x2"],p["y2"],p["x3"],p["y3"]=cx,cy-140,cx+120,cy+140,cx-120,cy+140
        elif "小" in text: p["x1"],p["y1"],p["x2"],p["y2"],p["x3"],p["y3"]=cx,cy-40,cx+40,cy+40,cx-40,cy+40
    if st is None: return None
    return {"intent":"draw","actions":[{"id":next_id(st[:3]),"type":st,"params":p}],"clarification":None,"source":"local"}

def parse_position(text: str, shape_type: str = "circle") -> tuple[int, int]:
    """解析方位，返回(cx,cy) for circle/polygon/triangle/text 或 (x,y) for rect"""
    # 9宫格坐标映射: 画布800×600
    pos_map = {
        "左上角": (130, 110), "左上": (130, 110),
        "正上方": (400, 100), "顶部中间": (400, 100), "上方": (400, 100), "顶上": (400, 100), "上边": (400, 100),
        "右上角": (670, 110), "右上": (670, 110),
        "左边": (130, 300), "左侧": (130, 300),
        "中间": (400, 300), "正中": (400, 300), "中心": (400, 300), "中央": (400, 300),
        "右边": (670, 300), "右侧": (670, 300),
        "左下角": (130, 490), "左下": (130, 490),
        "正下方": (400, 500), "底部中间": (400, 500), "下方": (400, 500), "下边": (400, 500), "底部": (400, 500),
        "右下角": (670, 490), "右下": (670, 490),
    }
    for kw, (cx, cy) in pos_map.items():
        if kw in text:
            return (cx, cy)
    return (400, 300)  # 默认中央

def parse_move_delta(text: str) -> tuple[int, int] | None:
    """解析相对位移指令，返回(dx,dy)或None"""
    dx, dy = 0, 0
    dist = 80  # 默认移动距离
    if "大" in text or "远" in text: dist = 150
    elif "小" in text or "近" in text: dist = 40
    if "左" in text and "右" not in text: dx = -dist
    if "右" in text and "左" not in text: dx = dist
    if "上" in text and "下" not in text: dy = -dist
    if "下" in text and "上" not in text: dy = dist
    if dx == 0 and dy == 0: return None
    return (dx, dy)

def adjust_pos(p: dict, text: str, st: str):
    cx, cy = parse_position(text, st)
    if st in ("circle", "line"):
        p["cx"] = cx; p["cy"] = cy
    elif st in ("rect", "text"):
        p["x"] = cx - 50; p["y"] = cy - 50
    elif st in ("triangle", "polygon", "star", "heart", "diamond", "pentagon", "hexagon"):
        # 这些形状用 cx/cy 定位，存入特殊字段
        p["cx"] = cx; p["cy"] = cy

# =====================================================
# System Prompt (强化版 — 支持复杂物体分解)
# =====================================================
SYSTEM_PROMPT = """你是一个超级智能的语音绘图助手。用户用自然语言描述想要的效果，你将其转化为精确的JSON操作。

## 画布: 800×600, 左上角为原点(0,0)
- 横向: x 0→800 (左→右)
- 纵向: y 0→600 (上→下)
- 默认线色 stroke=#000000, 线宽 strokeWidth=2, 填充 fill=transparent

## 9宫格方位映射
左上角左上: cx≈130,cy≈110 | 正上/顶上/上方: cx≈400,cy≈100 | 右上角右上: cx≈670,cy≈110
左侧/左边: cx≈130,cy≈300 | 正中/中间/中央: cx≈400,cy≈300 | 右侧/右边: cx≈670,cy≈300
左下角左下: cx≈130,cy≈490 | 正下/底下/下方: cx≈400,cy≈500 | 右下角右下: cx≈670,cy≈490

## 操作类型 (用这些type值)
1. circle: {cx,cy,r, stroke?,strokeWidth?,fill?}  ← 圆形
2. rect: {x,y,width,height, stroke?,strokeWidth?,fill?}  ← 矩形/方块
3. line: {x1,y1,x2,y2, stroke?,strokeWidth?}  ← 线段
4. triangle: {x1,y1,x2,y2,x3,y3, stroke?,strokeWidth?,fill?}  ← 三角形
5. polygon: {points:"x1,y1 x2,y2 ...", stroke?,strokeWidth?,fill?}  ← 星/心/菱/多边形
6. text: {x,y,content,fontSize?,fill?}  ← 文字
7. modify: {targetId, ...要改的新参数}  ← 修改颜色/大小/位置等属性
8. move: {targetId, dx,dy} 或 {targetId, x,y}  ← 移动
9. delete: {targetId}  ← 删除指定对象
10. copy: {targetId, dx?,dy?}  ← 复制，可选偏移
11. scale: {targetId, scale}  ← 缩放，1.5=放大1.5倍，0.5=缩小一半
12. clear: {}  ← 清空画布
13. undo: {}  ← 撤销

## 颜色 (必须用 #RRGGBB，不能用颜色名)
红:#FF0000 蓝:#0000FF 绿:#00FF00 黄:#FFFF00 黑:#000000 白:#FFFFFF
橙:#FF8800 紫:#8800FF 粉:#FF69B4 灰:#888888 棕:#8B4513 金:#FFD700
银:#C0C0C0 青:#00FFFF 天蓝:#87CEEB 深蓝:#000080 浅绿:#90EE90 深红:#8B0000

## 指代消解 (最重要!)
用户会说"那个红色圆"、"方块"、"最大的三角形"、"爱心"等来指代已有对象。
你必须仔细阅读〖画布状态〗中的历史对象，找到匹配的targetId。
- 按颜色找: params.fill 或 params.stroke 匹配的颜色对象
- 按形状找: type匹配的对象 (如"圆"→circle, "方块"→rect, "三角"→triangle, "爱心"→id含heart, "星星"→id含star等)
- 按大小找: "大的"→选尺寸最大的, "小的"→选最小的
- 按位置找: "上面的"→选y最小的, "左边的"→选x最小的
- 如果匹配多个，选最近创建的那个
- 如果找不到匹配对象，clarification写清楚让用户先画

## 自然语言理解规则
- "画个红色的圆" → circle + fill:#FF0000
- "在左边画蓝色方块" → rect + x≈100,y≈250 + fill:#0000FF
- "画一个大爱心" → polygon(心形) + 较大尺寸 + fill:#FF0000
- "把圆变成绿色" → modify targetId + fill:#00FF00
- "把爱心变大一点" → scale targetId + scale:1.3
- "把星星移到这里" → 根据上下文判断位置，无上下文则move到中间
- "删除那个红色方块" → delete targetId
- "复制这个圆" → copy targetId + dx:30,dy:30
- "画三个不同颜色的圆" → 3个circle action
- "把三角形放大一倍" → scale targetId + scale:2.0
- "把方块移到右下角" → move targetId + x:670,y:490
- "把爱心变小一半" → scale targetId + scale:0.5

## 尺寸参考
- 圆默认r:60, 大:r=100, 小:r=30
- 矩形默认120×90, 大:200×150, 小:60×45
- 文字默认fontSize:24, 大:40, 小:14
- 星/心/菱形等默认尺寸约60

## 复杂角色分解
奥特曼: 椭圆头(fill:#C0C0C0)+椭圆身体(fill:#FF0000)+黄圆眼×2+红三角+四肢rect
小黄人: 黄圆角矩形身体+蓝背带rect+白圆眼+灰护目镜+黑四肢
皮卡丘: 黄圆身体+红脸颊×2+黑三角耳×2+小圆眼+闪电尾polygon
哆啦A梦: 蓝椭圆身+白圆肚+白椭圆脸+红鼻+白圆眼×2
火箭: 尖三角+圆柱身rect+三角翼×3+火焰polygon

## 输出格式 (严格JSON，不要markdown代码块):
{"intent":"draw|modify|delete|clear|undo|copy|chat|clarify","actions":[{"id":"obj_N","type":"操作类型","params":{...}}],"clarification":null}"""

# =====================================================
# 模型
# =====================================================
class DrawRequest(BaseModel):
    instruction: str
    history: list[dict] = []

class DrawResponse(BaseModel):
    intent: str
    actions: list[dict]
    clarification: str | None = None
    source: str = "api"

def build_messages(instruction: str, history: list[dict]):
    m = [{"role":"system","content":SYSTEM_PROMPT}]
    if history:
        ht = "画布状态:\n"+json.dumps(history, ensure_ascii=False, indent=2)
        m.append({"role":"user","content":f"{ht}\n\n指令:\n{instruction}"})
    else:
        m.append({"role":"user","content":instruction})
    return m

@app.post("/api/parse")
async def parse_instruction(req: DrawRequest):
    local = local_parse(req.instruction, req.history)
    if local:
        return DrawResponse(intent=local["intent"], actions=local["actions"], clarification=local.get("clarification"), source="local")
    try:
        msgs = build_messages(req.instruction, req.history)
        resp = client.chat.completions.create(model="deepseek-chat", messages=msgs, temperature=0.1, max_tokens=2048)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            ls=raw.split("\n")
            raw="\n".join(ls[1:-1] if ls[-1].strip()=="```" else ls[1:]).strip()
        r = json.loads(raw)
        return DrawResponse(intent=r.get("intent","draw"), actions=r.get("actions",[]), clarification=r.get("clarification"), source="api")
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"LLM返回无效JSON: {raw[:200]}...")
    except Exception as e:
        raise HTTPException(500, f"解析失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status":"ok","mode":"hybrid"}

from pathlib import Path
app.mount("/", StaticFiles(directory=Path(__file__).parent, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)