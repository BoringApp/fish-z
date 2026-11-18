# 参考文档

[English](reference.md) | [简体中文](reference.zh-CN.md) · [返回 README](../README.zh-CN.md)

## 历史位置

历史保存在 `$XDG_DATA_HOME/fish-z/data`；
没有设置 `XDG_DATA_HOME` 时使用 `~/.local/share/fish-z/data`。

## 命令

| 命令 | 行为 |
| --- | --- |
| `z` | 列出历史目录；不会回到 Home |
| `z foo bar` | 按顺序匹配关键词，跳到最佳目录 |
| `z -c foo` | 仅搜索当前目录的子目录 |
| `z -e foo` | 输出目标路径，不跳转 |
| `z -l foo` | 列出匹配目录和分数 |
| `z -r foo` | 在同一匹配等级内按访问频率排序 |
| `z -t foo` | 在同一匹配等级内按最近访问时间排序 |
| `z --add /path/to/dir` | 手动记录一次访问 |
| `z -x` | 删除当前目录的历史记录 |
| `z -x /path/to/dir` | 删除指定目录的历史记录，即使目录已经不存在 |
| `z -xR /path/to/dir` | 删除该目录及其整个子树的历史记录 |
| `z -- -name` | 搜索以 `-` 开头的关键词 |
| `z -h` | 显示帮助 |

删除只影响跳转历史。`z -xR /` 会先询问是否清空全部历史。
`-r` 与 `-t` 不能同时使用。没有匹配时返回非零状态。

输入一个存在的绝对路径可以直接跳转；历史查找失败时也会尝试输入的相对目录。
包含空格的目录作为 `--add` 或 `-x` 的参数时需要加引号。

结果按目标目录名的匹配程度排序：完全匹配、开头匹配、中间包含、仅上层路径匹配。
同一等级内按访问频率和最近访问时间综合排序；`-r` 或 `-t` 则只使用其中一项。
祖先目录不会覆盖这个顺序。

多个关键词仍需按顺序匹配完整路径，最后一个非空关键词决定目标目录名的匹配等级；
关键词包含斜杠时，使用它的最后一个路径部分。目录名也支持 `*`、`?` 通配符。
历史路径末尾的斜杠不影响目录名判断；查询词末尾的 `/` 是否匹配目录本身，
仍由 `FISHZ_TRAILING_SLASH` 控制。

跳转和默认补全优先选择最佳结果。`-l`、`-lr` 将最佳结果显示在最后，`-lt` 则显示在最前。
列表中的 `common:` 行仅供参考。设置 `FISHZ_UNCOMMON=1` 后，会对已经选中的目标
裁掉末尾不包含查询词的层级。

## 配置

手动安装时，在加载插件前设置，例如：

```fish
set -g FISHZ_CASE ignore
set -g FISHZ_EXCLUDE_DIRS /tmp /private/tmp
set -g FISHZ_KEEP_DIRS /Volumes/Work
set -g FISHZ_ECHO 1
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

使用 Fisher 时，可以在交互式 fish 中通过 `set -U` 保存配置，例如：

```fish
set -U FISHZ_CASE ignore
```

设置后打开新的终端。这能让 `FISHZ_CMD` 等需要在插件加载前确定的配置及时生效。

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `FISHZ_CMD` | `z` | 命令名称，修改后重新加载插件 |
| `FISHZ_DATA` | 见上文 | 数据库的绝对路径 |
| `FISHZ_CASE` | `smart` | 大小写匹配模式：`smart`、`ignore` 或 `fallback` |
| `FISHZ_COMPLETION` | `frecent` | 按匹配等级和分数补全，或 `legacy` 按名称字母顺序排序 |
| `FISHZ_CD` | `builtin cd` | 自定义跳转命令，使用 fish 列表，例如 `set -g FISHZ_CD pushd` |
| `FISHZ_ECHO` | `0` | 跳转后输出当前路径 |
| `FISHZ_TILDE` | `0` | 输出时将 Home 前缀显示为 `~` |
| `FISHZ_EXCLUDE_DIRS` | 空列表 | 不记录这些目录及其子目录 |
| `FISHZ_KEEP_DIRS` | 空列表 | 即使暂时不存在也保留这些目录树 |
| `FISHZ_LOCK_TIMEOUT` | `1` | 等待写锁的秒数，允许小数 |
| `FISHZ_MAX_SCORE` | `9000` | 触发历史分数衰减的总分阈值 |
| `FISHZ_NO_RESOLVE_SYMLINKS` | `0` | 设为 `1` 保留目录的逻辑路径 |
| `FISHZ_TRAILING_SLASH` | `0` | 设为 `1` 后，`foo/` 也能匹配路径末尾的 `foo` |
| `FISHZ_UNCOMMON` | `0` | 启用按查询词裁剪已选中目标的行为 |

`smart` 在查询全小写时忽略大小写，包含大写字母时严格匹配。`ignore` 始终忽略大小写。
`fallback` 保留原来的行为：优先匹配大小写，找不到时再忽略大小写。
未设置或设为空的 `FISHZ_CASE` 使用 `smart`。

目录列表使用绝对路径，按路径边界匹配：排除 `/work` 不会排除 `/workshop`。

## 写入和恢复

每次写入在同一个目录锁内完成读取、修改和替换。读操作看到的是替换前或替换后的
完整文件。进程正常退出或收到 `TERM`、`INT`、`HUP` 时，会清理临时文件和目录锁。
写锁超时返回 `2`；自动记录静默跳过这次访问，手动 `z --add .` 可以查看错误。

fish 没有 zsh 的内置文件锁接口，因此这里使用目录锁。强制 `kill -9` 或断电可能
留下 `<数据库路径>.lock.d`，其 `owner` 文件记录写进程 PID。确认该进程已经结束后，
删除该锁目录中的 `owner` 文件，再用 `rmdir` 移除空锁目录。插件不会按文件年龄强抢锁。

数据库格式为 `绝对路径|频率|Unix 时间戳`；含 `|`、换行或回车的目录名无法记录。
数据库文件可以是符号链接，写入会更新其目标并保留链接。

## 与 zsh-z 的边界

- 默认采用智能大小写；设置 `FISHZ_CASE=fallback` 可恢复 zsh-z 默认的大小写优先规则。
- 目标目录名的匹配等级优先于访问分数，共同祖先目录不会覆盖选中的目标。
- 保留面向用户的主要命令行为，不模拟 zsh 的 ZLE、`zstyle` 或 shell 选项。
- 查询支持 `*`、`?`，空白在查询中充当通配符；行为不受 `qmark-noglob` 开关影响。
  不实现 zsh 的完整模式语法。
- 同一匹配等级内，`-t` 的列表和补全统一把最近访问的目录排在前面；分数相同的结果按路径确定顺序。
- 历史默认独立保存。虽然文件格式相同，但目录锁与 zsh-z 的文件锁不是同一种锁，
  不要让两个插件同时写同一个数据库。
- 暂不提供 zsh-z 的 `OWNER` / 提权代写配置，也不支持 Windows。
