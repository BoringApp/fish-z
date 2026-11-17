# fish-z

[English](README.md) | [简体中文](README.zh-CN.md)

**记住你常去的目录，用几个字母跳过去。**

fish-z 是 [BoringApp](https://github.com/BoringApp) 为 fish 编写的目录跳转插件，
以 [agkozak/zsh-z v2.0.1](https://github.com/agkozak/zsh-z/tree/v2.0.1) 为移植基准。
它沿用 zsh-z 的核心命令、frecency 排序思路和文本数据库格式，用 fish 的函数、
事件和补全接口实现日常使用体验。

```fish
z launch           # 跳到最匹配的常用目录
z project fish     # 按顺序匹配多个关键词
z -c src           # 只在当前目录下面搜索
z -l               # 看看记住了哪些目录
```

## 功能

- 按访问频率与最近访问时间综合排序，支持单独按频率或时间查找。
- 默认先匹配大小写，找不到时再忽略大小写；也支持 `ignore` 和 `smart` 模式。
- Tab 补全跟随搜索条件，并优先显示高分目录。
- 支持精确删除历史、递归删除子目录记录，以及清理已经不存在的目录。
- 可排除指定目录树，也可保留暂时离线的磁盘或挂载目录。
- 提示符触发后台记录；写入通过目录锁串行化，再用临时文件原子替换数据库。
- 数据文件权限为 `0600`，fish 私密模式不记录访问。

运行时使用 fish 和 macOS/Linux 的基础命令，不需要 Python、Node.js 或额外编译。
Python 只用于运行项目测试。

## 安装

目标环境为 fish 4.x，当前开发环境为 macOS、fish 4.9.3。
以下命令在 fish 终端中执行。选择手动安装或 Fisher 安装中的一种即可。

启用之前停用其他定义 `z` 的插件及其目录记录钩子，避免多个插件同时接管命令。
本项目采用独立的 `FISHZ_*` 配置，不读取旧 fish 插件的 `Z_*` 变量，也不会自动导入旧历史。

### 手动安装（推荐）

克隆到一个固定位置：

```fish
git clone https://github.com/BoringApp/fish-z.git ~/.local/share/fish-z/plugin
```

在 `~/.config/fish/config.fish` 中加入：

```fish
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

打开新的 fish 终端即可使用。如果没有旧插件正在运行，也可以在当前交互式 fish 中
执行这条 `source` 命令立即加载。项目可以放在其他目录，只需同步修改加载路径。

以后更新：

```fish
git -C ~/.local/share/fish-z/plugin pull --ff-only
```

更新后打开新的终端，加载新版函数。

### 使用 Fisher 安装

如果还没有安装 [Fisher](https://github.com/jorgebucaran/fisher#installation)，先执行：

```fish
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
```

安装 fish-z：

```fish
fisher install BoringApp/fish-z
```

Fisher 会安装函数和启动配置，不需要再向 `config.fish` 添加 `source` 行。

以后更新：

```fish
fisher update BoringApp/fish-z
```

### 开始使用

默认历史位置：

```text
$XDG_DATA_HOME/fish-z/data
```

没有设置 `XDG_DATA_HOME` 时使用 `~/.local/share/fish-z/data`。刚安装时历史为空，
正常进入几个工作目录后再使用 `z`。

## 命令

| 命令 | 行为 |
| --- | --- |
| `z` | 列出历史目录；不会回到 Home |
| `z foo bar` | 按顺序匹配关键词，跳到最佳目录 |
| `z -c foo` | 仅搜索当前目录的子目录 |
| `z -e foo` | 输出目标路径，不跳转 |
| `z -l foo` | 列出匹配目录和分数 |
| `z -r foo` | 按访问频率选择 |
| `z -t foo` | 按最近访问时间选择 |
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

默认模式下，如果一个匹配目录是所有其他匹配目录的祖先，会优先跳到该目录。
`FISHZ_UNCOMMON=1` 则选择最高分目录，并尝试去掉末尾不包含查询词的层级。

## 配置

手动安装时，在加载插件前设置，例如：

```fish
set -g FISHZ_CASE smart
set -g FISHZ_EXCLUDE_DIRS /tmp /private/tmp
set -g FISHZ_KEEP_DIRS /Volumes/Work
set -g FISHZ_ECHO 1
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

使用 Fisher 时，可以在交互式 fish 中通过 `set -U` 保存配置，例如：

```fish
set -U FISHZ_CASE smart
```

设置后打开新的终端。这能让 `FISHZ_CMD` 等需要在插件加载前确定的配置及时生效。

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `FISHZ_CMD` | `z` | 命令名称，修改后重新加载插件 |
| `FISHZ_DATA` | 见上文 | 数据库的绝对路径 |
| `FISHZ_CASE` | 空 | 默认大小写回退，或 `ignore` / `smart` |
| `FISHZ_COMPLETION` | `frecent` | 按分数补全，或 `legacy` 按名称排序 |
| `FISHZ_CD` | `builtin cd` | 自定义跳转命令，使用 fish 列表，例如 `set -g FISHZ_CD pushd` |
| `FISHZ_ECHO` | `0` | 跳转后输出当前路径 |
| `FISHZ_TILDE` | `0` | 输出时将 Home 前缀显示为 `~` |
| `FISHZ_EXCLUDE_DIRS` | 空列表 | 不记录这些目录及其子目录 |
| `FISHZ_KEEP_DIRS` | 空列表 | 即使暂时不存在也保留这些目录树 |
| `FISHZ_LOCK_TIMEOUT` | `1` | 等待写锁的秒数，允许小数 |
| `FISHZ_MAX_SCORE` | `9000` | 触发历史分数衰减的总分阈值 |
| `FISHZ_NO_RESOLVE_SYMLINKS` | `0` | 设为 `1` 保留目录的逻辑路径 |
| `FISHZ_TRAILING_SLASH` | `0` | 设为 `1` 后，`foo/` 也能匹配路径末尾的 `foo` |
| `FISHZ_UNCOMMON` | `0` | 启用按查询词裁剪最高分目标的行为 |

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

- 保留面向用户的主要命令行为，不模拟 zsh 的 ZLE、`zstyle` 或 shell 选项。
- 查询支持 `*`、`?`，空白在查询中充当通配符；行为不受 `qmark-noglob` 开关影响。
  不实现 zsh 的完整模式语法。
- `-t` 的列表和补全统一把最近访问的目录排在前面；分数相同的结果按路径确定顺序。
- 历史默认独立保存。虽然文件格式相同，但目录锁与 zsh-z 的文件锁不是同一种锁，
  不要让两个插件同时写同一个数据库。
- 暂不提供 zsh-z 的 `OWNER` / 提权代写配置，也不支持 Windows。

## 开发与测试

```sh
python3 -m unittest discover -s tests -v
```

测试使用临时 Home 和数据库，不读取或修改日常 shell 的跳转历史。
可选地设置 `ZSH_Z_REFERENCE=/path/to/zsh-z.plugin.zsh`，运行与上游的行为对照测试。

## 作者与来源

- fish 移植与项目维护：[BoringApp](https://github.com/BoringApp)
- 上游实现：[Alexandros Kozak / agkozak/zsh-z](https://github.com/agkozak/zsh-z)
- 原始工具：[rupa/z](https://github.com/rupa/z)

fish-z 是独立的 fish 移植项目，不是 zsh-z 官方发布的 fish 版本。
项目采用 [MIT License](LICENSE)，保留上游版权声明，并加入 BoringApp 对移植工作的版权署名。
