"""后端接口的请求封装：**一个分类一个文件**，页面只 import 分类模块，不自己发 HTTP。

- `client.py`   请求底座：基址、发请求（含 multipart 上传）、把后端的错误体翻成 `ApiError`
- `session.py`  登录态：access / refresh 令牌的存取（落库到 settings 表）
- `member_auth.py`  用户中心 · 认证：验证码 / 注册 / 登录 / 刷新 / 重置密码 / 当前会员 / 登出
- `member_profile.py`  用户中心 · 资料：查看 / 修改资料、上传头像
- `member_countdowns.py`  用户中心 · 倒数日：列表 / 新增 / 修改 / 删除

对应后端 fastapi-admin-backend 的 `app/api/v1/endpoints/member_auth.py`；接口
前缀是 `/api/v1`（见后端 `app/core/config.py` 的 `API_V1_PREFIX`）。
再加一个分类 = 再放一个同级的 `xxx.py`。
"""
