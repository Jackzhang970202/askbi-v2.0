"""
人力资源效能分析大屏预览服务器
启动: python server.py
停止: Ctrl+C
可选参数:
  --no-browser  不自动打开浏览器
  --port 9000   指定端口（默认8888）
"""
import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8888
DIR = os.path.dirname(os.path.abspath(__file__))

# 解析端口参数
if "--port" in sys.argv:
    idx = sys.argv.index("--port")
    if idx + 1 < len(sys.argv):
        PORT = int(sys.argv[idx + 1])

os.chdir(DIR)


class Handler(http.server.SimpleHTTPRequestHandler):
    """自定义Handler: favicon重定向到shared目录，抑制favicon 404"""

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.path = "/shared/favicon.ico"
        # 默认重定向到style4
        if self.path == "/" or self.path == "":
            self.path = "/style4_business_cyan/"
        super().do_GET()

    def log_message(self, format, *args):
        # 过滤掉favicon的日志
        if "favicon" not in str(args):
            super().log_message(format, *args)


# 允许端口复用
socketserver.TCPServer.allow_reuse_address = True

print("=" * 60)
print("  人力资源效能分析大屏预览服务器")
print("=" * 60)
print()
print(f"  服务目录: {DIR}")
print(f"  端口: {PORT}")
print()
print(f"  访问地址: http://localhost:{PORT}/")
print()
print("  Ctrl+C 停止服务器")
print("=" * 60)

# 自动打开浏览器
if "--no-browser" not in sys.argv:
    webbrowser.open(f"http://localhost:{PORT}/")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.server_close()