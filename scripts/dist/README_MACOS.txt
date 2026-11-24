BossHunter portable package (macOS)
===================================

首次使用
--------
1. 解压本压缩包到任意位置（例如 ~/BossHunter）：
   tar -xzf BossHunter-*-macos-*.tar.gz -C BossHunter
2. 双击 BossHunter/scripts/start_macos.command。
   首次运行若被 Gatekeeper 拦截，请在终端执行：
   xattr -d com.apple.quarantine BossHunter/scripts/start_macos.command
3. 工作台会在浏览器中打开：http://127.0.0.1:8686

无需安装 Python、Node.js、Git，也无需运行 npm/pip 命令——运行所需的
Python、依赖、前端资源与 Node.js（patchright 自带）已全部包含在内。

数据保存
--------
配置（config.yaml）和岗位数据（data/）保存在本目录，关闭、再次启动
及版本更新后都会保留。升级版本时解压新包后复制旧目录的 config.yaml
和 data/ 即可。

Chrome
------
岗位采集需要 Chrome 及远程调试。启动器会自动启动一个专用 Chrome
窗口（独立用户目录，不影响日常使用的 Chrome）。请在浏览器中手动
登录招聘平台并完成 AI 配置——所有发送都需人工确认。

常见问题
--------
- 提示端口 8686 被占用：关闭其他 BossHunter 实例，或修改 config.yaml
  中的 web 端口配置。
- 提示找不到 Chrome：安装 Chrome 后重新运行启动器。
- aarch64 包用于 Apple Silicon（M1/M2/M3/M4）；Intel Mac 请下载
  x86_64 包。