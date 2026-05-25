# 手机访问 ValuationMonitor

## 推荐方案：Tailscale（零配置 VPN，免费）

Tailscale 把你的所有设备（笔记本 + 手机）放入一个虚拟私有网络。手机访问笔记本上的服务时，
就像在同一个 WiFi 一样，**不暴露到公网**。

### Step 1：在 Linux 笔记本上装 Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# 命令会打印一个浏览器登录 URL，用 Google / GitHub / 邮箱登录
```

登录后 `tailscale ip -4` 会显示你笔记本的 Tailscale IP（形如 `100.x.x.x`）。

### Step 2：让 uvicorn 监听该 IP（而不是只听 127.0.0.1）

最简方案 — 监听 0.0.0.0（让 Tailscale 网络 + 本地 WiFi 都能连）：

```bash
cd ~/ValuationMonitor
backend/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

更安全方案 — 只监听 Tailscale IP（仅 Tailscale 网络内可见）：

```bash
TS_IP=$(tailscale ip -4)
backend/.venv/bin/uvicorn backend.app.main:app --host $TS_IP --port 8000
```

### Step 3：手机装 Tailscale APP + 登录同一账号

- iOS：App Store 搜 "Tailscale"
- Android：Google Play 同名

登录后手机会显示笔记本的 Tailscale IP，例如 `100.94.12.34`。

### Step 4：手机浏览器访问

```
http://100.94.12.34:8000
```

✅ 完成。不论你在地铁、咖啡店、办公室，只要手机和笔记本都开着 Tailscale，就能访问。

---

## 备选：HTTPS + 公网

如果你想任何人都能访问（不推荐 — 数据库含个人投资信息）：

- Caddy / Nginx 反向代理 + Let's Encrypt 自动 HTTPS
- 加 Basic Auth：
  ```caddyfile
  yourdomain.com {
      reverse_proxy 127.0.0.1:8000
      basicauth {
          cindy $2a$14$xxxxxxxxxxx  # caddy hash-password 生成
      }
  }
  ```

SRS D8 明确：**默认 localhost-only**，公网访问需用户主动配置。

---

## 安全注意

- Tailscale 把你的设备放入私有网络，**默认不暴露到公网**。即使监听 0.0.0.0，公网用户也无法直连。
- 但如果你在公开 WiFi（如机场）+ 监听 0.0.0.0，**同 WiFi 用户可以扫到 8000 端口并访问**。
  - 解决：用 Tailscale IP 监听（Step 2 第二个命令），不监听 0.0.0.0。
- 不要把 Tushare token 等敏感凭证写到任何公开访问的页面。本工具已经避免显示 token。

---

## 常见问题

**Q: 笔记本休眠后连不上？**
A: Tailscale 唤醒延迟约 1-3 秒。如果服务（uvicorn）也被休眠停了，需要笔记本上重新启动 uvicorn。

**Q: 速度慢？**
A: Tailscale 通常走 P2P 直连，速度 = 你两设备网络的瓶颈。第一次连接可能走中继（DERP）慢 0.5 秒，后续会自动优化到直连。

**Q: 多人共享？**
A: Tailscale 同一账号支持加入多设备。如果想给家人加入，可以邀请他们以 Guest 身份加入你的 tailnet。
