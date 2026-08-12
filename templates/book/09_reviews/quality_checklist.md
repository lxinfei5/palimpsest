# 续写 / 改写验收清单

写完一章后先跑：

```text
palimpsest quality <book-id> [--chapter c004]
```

未指定 `--chapter` 时检查最新一篇 `continue` / `rewrite`。

## 机器门（`palimpsest quality`）

- [ ] 章节文件存在于 `05_manuscript/volumes/**` 或 `05_manuscript/original/`
- [ ] YAML front matter 含 `id`、`kind`
- [ ] `kind` 为 `continue` 或 `rewrite`（其它 kind 视为结构错误）
- [ ] 续写有 `source_after`；改写有 `source` 或 `source_chapter`
- [ ] 对照 `04_outline/continue_brief.md` 或 `rewrite_brief.md` 的目标字数（缺 brief 或偏离仅为警告）
- [ ] `08_sessions/` 有提到本章或 `task: continue` / `task: rewrite` 的日志
- [ ] 该日志含标题 `Input` / `Actions` / `Open questions`（缺标题为警告）

缺章、kind 非法、缺必填 front matter → 退出码 1。警告不导致失败。

## 人工门（对照 AGENTS §5.4 / §5.5）

- [ ] 读过 book.yaml、相关 canon、continuity、brief、近 1–3 章
- [ ] 续写落在 `05_manuscript/volumes/continue/`，改写落在 `volumes/rewrite/`，未覆盖 original
- [ ] `volume.yaml` 已维护
- [ ] 已更新 `03_continuity/character_states.yaml` 与 `open_threads.yaml`
- [ ] 未静默改 canon；必要改设定已写入 `canon_change_requests.md` 或已向用户确认
- [ ] 文风与 brief 约束一致；禁止发生的情节未出现
