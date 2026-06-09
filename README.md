# 日省 · 通杀牌的个人日志

暗色极简 · 密码保护 · GitHub Pages 托管

## 使用方法

### 写日记
在 `entries/` 目录下创建 `YYYY-MM-DD.md` 文件：

```markdown
# 标题（可选）
今天的内容...
- 要点1
- 要点2
```

### 构建网站
```bash
python build.py <你的密码>
```
生成 `docs/index.html`（密码加密的静态页面）

### 发布
```bash
git add -A && git commit -m "新日记" && git push
```
GitHub Pages 自动从 `docs/` 目录部署。

### 本地预览
直接用浏览器打开 `docs/index.html`。

## 安全
- 密码通过 SHA-256 哈希存储在页面中
- 解锁后内容在浏览器内存中，不发送到任何服务器
- 适合个人日志，不适合极高安全需求场景
