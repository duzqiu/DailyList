"""**与页面相关**的部分都在这儿（见 README「开发约定」2、3）；与页面无关的工具类在 `tools/`。

- **共享组件**（一份实现、多处使用）：登录 / 注册 / 忘记密码三页的表单骨架
  (`auth_form.py`)、设置卡片 (`settings_card.py`)、倒数日卡片与弹窗
  (`countdown_card.py` / `countdown_form.py`)、下拉选择器 (`popup_select.py`)、
  系统选择器 (`pickers.py`)、左滑行 (`swipe_delete.py`)、左滑返回 (`swipe_back.py`)、
  toast (`toast.py`)
- **`layout.py`**：全局配色 / 尺寸常量、assets 路径、二级页顶栏、弹窗键盘定位、
  `is_attached` / `safe_update` 这些页面级小工具
- **`my_background.py`**：「我的」页那段的背景图（存路径 + 铺图）
- **`services.py`**：页面级 Service（剪贴板 / 文件选择器）的注册与取用

页面和组件引用它们都走 `widgets.*`；真正与页面无关的东西（数据、设备、农历、版本检查
等等）仍从 `tools.*` 取。
"""
