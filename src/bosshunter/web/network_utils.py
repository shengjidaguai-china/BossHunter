"""网络工具 - 局域网 IP 检测与手机扫码二维码生成"""

import socket
from typing import List


def get_lan_ips() -> List[str]:
    """获取本机所有可用的局域网 IPv4 地址，按优先级排序。"""
    candidates = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in candidates:
                candidates.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        route_ip = s.getsockname()[0]
        s.close()
        if route_ip and not route_ip.startswith("127.") and route_ip not in candidates:
            candidates.insert(0, route_ip)
    except Exception:
        pass

    def _sort_key(ip: str) -> int:
        if ip.startswith("10.") or ip.startswith("192.168."):
            if ".56." in ip or ".198." in ip or ".65." in ip or ".255." in ip:
                return 5
            return 1
        if ip.startswith("172."):
            return 2
        return 10

    candidates.sort(key=_sort_key)
    return candidates or ["127.0.0.1"]


def render_terminal_qr(url: str) -> str:
    """生成适用于控制台打印的二维码字符串（使用 ANSI 空格背景色块，避免字符集乱码）。"""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        matrix = qr.get_matrix()
        
        lines = []
        for row in matrix:
            line_parts = []
            for cell in row:
                if cell:
                    line_parts.append("\033[40m  \033[0m")
                else:
                    line_parts.append("\033[47m  \033[0m")
            lines.append("".join(line_parts))
        return "\n".join(lines)
    except Exception:
        return ""


def print_mobile_banner(host: str, port: int, show_qr: bool = True):
    """打印手机端连接横幅与扫码指引。"""
    lan_ips = get_lan_ips()
    primary_lan_ip = lan_ips[0] if lan_ips else "127.0.0.1"

    print()
    print("=" * 60)
    print(" 🚀 BossHunter 控制台已启动")
    print("=" * 60)
    print(f" 💻 电脑本机访问: http://127.0.0.1:{port}")
    if primary_lan_ip != "127.0.0.1":
        mobile_url = f"http://{primary_lan_ip}:{port}"
        print(f" 📱 手机端访问:   \033[1;32m{mobile_url}\033[0m")
        if len(lan_ips) > 1:
            other_ips = ", ".join(f"http://{ip}:{port}" for ip in lan_ips[1:3])
            print(f"    (其他可用网卡: {other_ips})")
        print()
        print(" 💡 手机端连接说明:")
        print("   1. 手机需与电脑连接同一 Wi-Fi 局域网")
        print("   2. 手机打开相机或微信，直接扫描下方二维码访问")
        print("   3. 可在手机浏览器菜单中选择「添加到主屏幕」，即可全屏秒开")
        
        if show_qr:
            qr_text = render_terminal_qr(mobile_url)
            if qr_text:
                print()
                print(qr_text)
                print()
    else:
        print(" ⚠️  未检测到可用局域网网卡，当前仅限本机访问")
    print("=" * 60)
    print()
