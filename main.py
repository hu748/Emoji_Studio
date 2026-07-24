import argparse
import os
import sys
from config import BASE_DIR, SAVE_DIR


def run_web_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    print(f"🌐 启动Web界面：http://{host}:{port}")
    print(f"📁 输出目录：{SAVE_DIR}")
    uvicorn.run("app:app", host=host, port=port, reload=False)


def run_cli_demo(img_path: str, platform: str = "wechat", dynamic: str = "shake",
                 text: str = None, use_agent: bool = False, prompt: str = None):
    if not os.path.exists(img_path):
        print(f"❌ 图片不存在：{img_path}")
        sys.exit(1)
    from emoji_agent import create_emoji_agent, process_with_agent, rule_based_process

    if use_agent or prompt:
        agent = create_emoji_agent(verbose=True)
        if not prompt:
            prompt = f"处理图片 {img_path}，抠图，适配{platform}尺寸，美化，添加文字{text or '无'}，生成{dynamic}动图并压缩"
        print(f"🧠 使用智能体处理，指令：{prompt}")
        result = process_with_agent(prompt, agent=agent)
    else:
        print(f"⚙️ 使用规则模式处理图片：{img_path}")
        result = rule_based_process(img_path, platform, dynamic, text)
    print(f"✅ 处理结果：{result}")


def run_batch(folder: str, platform: str = "wechat", text: str = None):
    if not os.path.isdir(folder):
        print(f"❌ 文件夹不存在：{folder}")
        sys.exit(1)
    from emoji_agent import get_skill_instance
    skill = get_skill_instance()
    result = skill.batch_process_emoji.invoke({
        "folder_path": folder,
        "platform": platform,
        "add_text": text,
    })
    print(result)


def run_tool(tool_name: str, **kwargs):
    from emoji_agent import get_skill_instance
    skill = get_skill_instance()
    if not hasattr(skill, tool_name):
        print(f"❌ 工具不存在：{tool_name}")
        print("可用工具：")
        for attr in dir(skill):
            if not attr.startswith("_") and callable(getattr(skill, attr)):
                print(f"  - {attr}")
        sys.exit(1)
    tool = getattr(skill, tool_name)
    print(f"🔧 调用工具：{tool_name} 参数：{kwargs}")
    result = tool.invoke(kwargs)
    print(f"✅ 结果：{result}")


def main():
    parser = argparse.ArgumentParser(description="表情包动图生成器智能体 · Emoji Studio")
    sub = parser.add_subparsers(dest="command", help="子命令")

    p_web = sub.add_parser("web", help="启动Web界面")
    p_web.add_argument("--host", default="0.0.0.0")
    p_web.add_argument("--port", type=int, default=8000)

    p_cli = sub.add_parser("cli", help="命令行处理单张图片")
    p_cli.add_argument("image", help="图片路径")
    p_cli.add_argument("--platform", choices=["wechat", "qq"], default="wechat")
    p_cli.add_argument("--dynamic", choices=["shake", "bounce", "breathe", "static"], default="shake")
    p_cli.add_argument("--text", help="添加文字")
    p_cli.add_argument("--agent", action="store_true", help="使用智能体模式")
    p_cli.add_argument("--prompt", help="自定义自然语言指令")

    p_batch = sub.add_parser("batch", help="批量处理文件夹内图片")
    p_batch.add_argument("folder", help="图片文件夹路径")
    p_batch.add_argument("--platform", choices=["wechat", "qq"], default="wechat")
    p_batch.add_argument("--text", help="批量添加文字")

    p_tool = sub.add_parser("tool", help="直接调用单个Skill工具")
    p_tool.add_argument("tool_name", help="工具名称，例如 remove_bg / resize_emoji / shake_gif_from_single")
    p_tool.add_argument("--kwargs", nargs="*", help="参数，格式 key=value key2=value2 ... 列表用逗号分隔")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        print("\n📌 使用示例：")
        print("  python main.py web                    # 启动Web界面 (推荐)")
        print("  python main.py cli test.png           # 处理单张图片")
        print("  python main.py cli test.png --text 哈哈 --platform qq")
        print("  python main.py batch ./images --text 冲鸭")
        print("  python main.py tool remove_bg img_path=test.png")
        sys.exit(0)

    if args.command == "web":
        run_web_server(args.host, args.port)
    elif args.command == "cli":
        run_cli_demo(args.image, args.platform, args.dynamic, args.text, args.agent, args.prompt)
    elif args.command == "batch":
        run_batch(args.folder, args.platform, args.text)
    elif args.command == "tool":
        kwargs = {}
        if args.kwargs:
            for kv in args.kwargs:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if "," in v:
                        kwargs[k] = v.split(",")
                    elif v.isdigit():
                        kwargs[k] = int(v)
                    elif v.lower() in ("true", "false"):
                        kwargs[k] = v.lower() == "true"
                    else:
                        try:
                            kwargs[k] = float(v)
                        except ValueError:
                            kwargs[k] = v
        run_tool(args.tool_name, **kwargs)


if __name__ == "__main__":
    main()
