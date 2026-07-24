# 🍬 CANDY 表情包工坊 · Emoji Studio

> 基于 Python + LangChain 智能体 + FastAPI 的 **微信 / QQ 动图表情包一键生成器**  
> Y2K 糖果玻璃拟态风格 UI，支持「单图精修 / 批量处理 / 多图合成 GIF / 智能体自然语言调度」四种工作流

---

## ✨ 一句话能做什么

把一张（或一整个文件夹的）普通图片 → **自动抠背景 → 适配微信/QQ 尺寸 → 美化提亮磨皮 → 加文字贴纸 → 生成抖动摇摆 / 弹跳缩放 / 呼吸淡入等动效 → 压缩到微信可发的 500KB 以内**，最终产出可直接在聊天里发送的表情包图片 / GIF。

| 📸 输入 | ✨ 处理 | 🎁 输出 |
|---|---|---|
| JPG / PNG / WEBP 图片 | 抠图·美化·加字·动效·压缩 | 适配微信 240×240 / QQ 320×320 的 PNG / GIF |
| 多张图片文件夹 | 批量一键全部处理 | 打包 ZIP 下载，每张都可单独预览 |
| 按顺序排列的一组图 | 按帧合成 GIF，可选帧时长·循环次数 | 合成动图 GIF，自带统一尺寸 + 压缩 |

---

## 🧱 技术栈

| 层 | 技术 |
|---|---|
| 智能体调度 | **LangChain**（AgentType 结构化 ReAct） |
| 大模型 | 任何 OpenAI 兼容 API（通过 `OPENAI_API_KEY` 环境变量接入） |
| 图像处理 | **Pillow**（PIL）+ **OpenCV** + **imageio** + **rembg**（AI 抠图） |
| Web 后端 | **FastAPI** + **uvicorn** |
| 前端 | 原生 HTML / CSS / JS，Y2K 糖果液态玻璃拟态风格，**零前端框架依赖** |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd gentert_image
pip install -r requirements.txt
```

> 💡 可选增强：如果需要真正的 AI 抠图效果（而不是透明直出），请确保 `rembg` 安装成功：
> ```bash
> pip install rembg onnxruntime
> ```
> 首次抠图会自动下载 U²-Net 模型（约 176MB）。

### 2. 启动 Web 界面（推荐）

```bash
python main.py web --host 127.0.0.1 --port 8000
```

浏览器打开 http://127.0.0.1:8000/ 即可。

### 3. （可选）启用智能体模式

设置环境变量后即可在前端勾选「🧠 开启智能体模式」，用自然语言指导处理流程：

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-你的key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"   # 或任何兼容地址

# macOS / Linux
export OPENAI_API_KEY="sk-你的key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

---

## 🧩 功能清单（13 个核心 Skill 工具）

### 🔧 基础加工
| # | 工具名 | 作用 | 关键参数 |
|---|---|---|---|
| 1 | 图片背景抠图技能 | 用 AI 移除背景，输出透明底 PNG | `img_path` |
| 2 | 表情尺寸适配技能 | 按平台等比缩放到标准尺寸 | `platform`: wechat(240²) / qq(320²) |
| 3 | 静态表情美化技能 | 提亮 + 双边滤波磨皮 | `bright`(0–50), `smooth`(T/F) |
| 4 | 动图压缩适配微信发送 | 循环降采样 + 缩尺寸至 ≤500KB | `max_size_kb`(默认 500) |

### 🎬 动效生成
| # | 工具名 | 效果 | 参数 |
|---|---|---|---|
| 5 | 单图逐帧抖动动图技能 | 轻微随机位移的抖动摇摆（最常用） | `frame_num`(默认 6) |
| 6 | 弹跳动图技能 | 正弦缩放的弹跳 Q 弹动效 | `scale_range`(0–1, 默认 0.2) |
| 7 | 呼吸淡入动图技能 | 透明度渐变呼吸动效 | `frame_num`(默认 10) |
| 8 | 多图合成 GIF 动图技能 | 多张图片按顺序合成一帧一张的动画 | `duration`(秒), `loop`(0=∞) |

### 🎨 美化装饰
| # | 工具名 | 作用 | 参数 |
|---|---|---|---|
| 9 | 文字贴纸添加技能 | 给表情包加文字（自带描边+自动找字体） | `position`(top/center/bottom), `font_size`, `font_color`, `stroke_width` |
| 10 | 特效变换技能 | flip_h/v 翻转 · rotate_90/180 · mirror 镜像 · fisheye 鱼眼 · grayscale 黑白 · sepia 怀旧 · blur 模糊 · sharpen 锐化 | `effect` 选一个 |
| 11 | 边框装饰技能 | rounded 圆角 · solid 直线框 · dashed 虚线框 · neon 霓虹光晕（多层模糊发光） | `style`, `border_width`, `border_color`, `shadow`, `bg_color` |

### 📦 批量 & 一键全流程
| # | 工具名 | 作用 |
|---|---|---|
| 12 | 批量生成表情包技能 | 给一个文件夹，一键把所有图片全部走完「抠图→适配→美化→加字→抖动」流程 |
| 13 | 全流程表情包生成技能 | 单张一键走完全链路，动效类型可选（shake/bounce/breathe/static），可选是否加字和压缩 |

---

## 🖥 Web 界面操作指南

### Tab 1：🖼 单图精修（最常用）

```
① 上传图片
   ├─ 🖱 点击选择 / 📤 拖拽上传 任意一个都行
   └─ 支持 JPG / PNG / WEBP / BMP
② 选参数
   ├─ 🎯 目标平台：微信 240×240 / QQ 320×320
   ├─ 🎬 动效类型：🍭 抖动摇摆 / 🪀 弹跳缩放 / 🌬 呼吸淡入 / 🖼 静态
   ├─ 💬 文字（可选）：例如「哈哈哈 / 贴贴 / 冲鸭 / 老板 666」
   ├─ 📍 文字位置：底部压住 / 顶部压住 / 居中霸屏
   └─ 🧠 智能体模式（可选，配好 KEY 才能勾选）
③ 点 ✨ 开始生成表情包
④ 结果区预览 → 右键保存 / 点 下载 按钮
   └─ 右侧「🧾 历史作品」会列出生成过的所有图，点 🔄 刷一刷 可刷新
```

### Tab 2：📁 批量 / 合成

这里有**两种模式**，点切换按钮可左右切换：

#### 模式 A：批量处理一整个文件夹
- 上传方式：「上传整个文件夹」或「多选多个图片」两种都可以
- 功能：
  - 勾选全部图片 / 单个取消勾选
  - 调整顺序（上移 / 下移 / 置顶 / 置底）
  - 选项：
    - 动效类型 / 帧时长 / 循环次数
    - 是否对每张图都加相同文字，或**每张图单独设置文字**（👉点「✏️ 为每张图单独设置文字」）
    - 目标平台：微信 / QQ
    - 智能体模式开关
- 结果：全部生成完会打包成 **ZIP** 一键下载，同时每张图可单独预览

#### 模式 B：多图合成 GIF
- 用途：一组按顺序排列的静态图 → 合成一个连贯 GIF（把朋友的照片串起来当表情包超好玩 😄）
- 参数：
  - 🎠 帧时长：150ms 快速 / 300ms 正常 / 500ms 慢速
  - 🔁 循环次数：∞ 无限 / 1 次就停
  - 可选：统一尺寸到微信/QQ、给每一帧都加相同文字
- 结果：合成 GIF + 自动压缩，直接下载发送

### 🧠 智能体模式 vs 规则模式

| 维度 | 🧠 智能体模式 | ⚙️ 规则模式（默认） |
|---|---|---|
| 依赖 | 需要 `OPENAI_API_KEY` + 能访问 LLM | 零配置，开箱即用 |
| 处理方式 | LLM 解析自然语言指令，**自己规划先调用什么工具再调用什么工具** | 固定流水线：抠图→适配→美化→加字→动效→压缩 |
| 灵活度 | 极高——可以说「给这张图做鱼眼特效，加霓虹粉边框，加字『yyds』居中，做成弹跳动效不压缩」 | 中——按前端勾选的参数线性执行 |
| 速度 | 慢（需要调用大模型推理 + 中间思考） | 快（纯图像处理，无需 LLM 调用） |
| 稳定性 | 偶尔会走错步骤（需要准确指令） | 100% 稳定，每次结果一致 |
| 适用人群 | 想玩花样、一句话描述创意、批处理混合需求 | 日常使用、追求稳定和速度 |

---

## 🖥 命令行（CLI）使用方式

不想开浏览器也能用命令行直接处理：

### 1) 单张图片（规则模式，推荐日常）
```bash
python main.py cli _sample/小红.png
# 指定：加文字 + QQ 平台 + 弹跳动效
python main.py cli _sample/小红.png --text 冲鸭 --platform qq --dynamic bounce
```

### 2) 单张图片（智能体模式，自然语言指令）
```bash
python main.py cli _sample/小红.png --agent --prompt "抠图做成微信尺寸，加蓝色霓虹边框，加文字『贴贴』放中间，做成呼吸动效，压缩"
```

### 3) 批量处理整个文件夹
```bash
python main.py batch _sample --text 哈哈哈 --platform wechat
```

### 4) 直接调用单个 Skill 工具
```bash
python main.py tool remove_bg img_path=_sample/小红.png
python main.py tool apply_effect img_path=xxx.png effect=fisheye
python main.py tool add_border_decoration img_path=xxx.png style=neon border_color=pink
python main.py tool make_gif_emoji img_list=a.png,b.png,c.png duration=0.2 loop=0
```

工具参数格式：`key=value`；多个参数空格分开；列表用逗号分隔。

---

## 📁 项目结构

```
gentert_image/
├── main.py                # 入口：CLI 子命令解析 & Web 启动
├── app.py                 # FastAPI 后端：所有 /api/* 接口
├── config.py              # 全局常量：尺寸、目录、PIL↔cv2 互转工具
├── emoji_skills.py        # 核心：13 个 Skill 工具函数 + EmojiMakerSkill 容器类
├── emoji_agent.py         # 智能体：LangChain agent 创建 + 规则模式兜底
├── requirements.txt       # 依赖清单
├── .gitignore             # GitHub 上传忽略规则（见下方）
├── templates/
│   └── index.html         # 前端单页：Y2K 糖果液态玻璃拟态 UI
├── upload/                # 运行时：上传图片临时存放（不上传 GitHub）
├── emoji_output/          # 运行时：所有生成结果（不上传 GitHub）
└── _sample/               # 几张示例图（用来快速测试）
```

### 关键 API（后端接口，供参考）

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/` | 前端主页 |
| `POST` | `/api/upload` | 单文件上传 |
| `POST` | `/api/upload_batch` | 多文件上传（返回 batch_id） |
| `POST` | `/api/generate` | 单图精修：生成一张表情包 |
| `POST` | `/api/generate_batch` | 批量处理：生成多个 + ZIP 打包 |
| `POST` | `/api/combine_gif` | 多图合成 GIF |
| `POST` | `/api/run_agent` | 智能体模式：自然语言指令处理 |
| `GET` | `/output/<file>` | 静态文件：生成结果访问 |
| `GET` | `/api/history` | 历史作品列表 |

---




## ❓ 常见问题 FAQ

**Q：为什么抠图没生效？输出和原图一样？**  
A：`rembg` 没装好或缺少 `onnxruntime`。执行 `pip install rembg onnxruntime`，重启后首次抠图会自动下载模型。如果装不上，程序会跳过抠图直接继续后面的步骤，不会报错中断。

**Q：生成的 GIF 微信发不出去？**  
A：微信单张表情建议 ≤ 500KB。工具 `compress_gif` 默认就会压到 500KB 内。如果还是太大，可以：① 选微信平台（更小尺寸）② 动效帧数调少 ③ 静态表情直接发 PNG。

**Q：字体是乱码 / 问号？**  
A：Windows 会优先用微软雅黑 msyh.ttc，macOS 用 PingFang.ttc，Linux 用 DejaVu。如果都找不到就退回 PIL 默认字体（通常不支持中文）。想完全自定义可改 `emoji_skills.py` 里的 `_load_font()` 指向自己的 ttf 路径。

**Q：智能体模式下结果总是不对？**  
A：指令越具体越好，试试在 prompt 里把「做什么操作 / 顺序 / 参数」都写出来。也可以先在规则模式里玩熟练，再切智能体尝试创意组合。

---

## 🛠 自定义拓展建议

代码非常模块化，加新功能超简单：

1. **加一个新动效**：去 `emoji_skills.py` 照着 `bounce_gif_from_single` 再写一个类似的 `@tool`，然后加入 `_ALL_TOOL_FUNCS` 列表和 `EmojiMakerSkill` 类 → 前端加一个 option，完事。
2. **加新特效变换**：`apply_effect()` 里的 `if/elif` 再加一个分支即可。
3. **加新边框样式**：`add_border_decoration()` 的 `style` 再加一个分支即可。
4. **换前端主题**：`templates/index.html` 顶部的 `:root` CSS 变量集中管理颜色，改 `--candy-c1 ~ c5` 五个颜色就能整体换肤。

Have fun and 生成一堆可爱表情包去轰炸朋友们的聊天框吧！🍭🍬🎉
