# obsidian-capture Skill for Marvis

## 触发条件

用户发送包含以下 URL 模式的消息时触发：

- `https://mp.weixin.qq.com/s/...`
- `https://v.douyin.com/...` 或 `https://www.douyin.com/...`
- `https://zhuanlan.zhihu.com/...` 或 `https://www.zhihu.com/...`
- `https://arxiv.org/...pdf` 或 `https://arxiv.org/abs/...`
- `https://blog.csdn.net/...`
- `https://sspai.com/...`

## 前置条件

- `obsidian-capture` CLI 已安装（`pip install obsidian-capture`）
- `~/.obsidian-capture/config.yaml` 已配置 `obsidian.vault_dir`
- 如需抖音支持，已配置 `sources.douyin.api_url` 指向本地 API

验证方法：

```bash
capture --version  # 检查 CLI 是否安装
python -c "from capture import __version__; print(__version__)"
```

## 执行策略

收到符合触发条件的 URL 时：

1. 直接执行 `capture "<URL>"`
2. 将 CLI 的标准输出原样展示给用户
3. 若 CLI 返回非零 exit code，将 stderr 错误信息呈现给用户
4. 无需预先识别来源，CLI 内部自动处理
5. 无需询问用户确认，直接执行

## 示例

**用户**: `https://mp.weixin.qq.com/s/AUWscgxJHTbgVSzwEp6GEA`

**执行**: `capture "https://mp.weixin.qq.com/s/AUWscgxJHTbgVSzwEp6GEA"`

**输出**: `OK 已入库: D:\...\01-文章\公众号\闲搞机-末代双系统MacBookPro无头骑士-20260629.md`

## 故障排除

| 错误 | 可能原因 | 解决方法 |
|------|---------|---------|
| `capture: command not found` | CLI 未安装 | `pip install obsidian-capture` |
| `obsidian.vault_dir 未配置` | 配置文件不存在或未填写 | `capture --init` 然后编辑配置 |
| `Obsidian 库路径不存在` | vault_dir 指向了不存在的路径 | 检查并修正 config.yaml 中的路径 |
| `抖音 API 不可达` | 本地抖音 API 未启动 | 启动 obsidian-content-capture-backend 或其他后端 |
