import os
import pathlib
import sys

# 测试环境使用开发态配置，避免生产 JWT_SECRET 校验拦截
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")

# 保证可以 import app.*（无需安装为包）
_backend_dir = pathlib.Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
