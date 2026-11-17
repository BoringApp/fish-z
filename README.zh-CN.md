# fish-z

[English](README.md) | [简体中文](README.zh-CN.md)

我在 Zsh 中最喜欢的命令 [zsh-z](https://github.com/agkozak/zsh-z)，现在也有原生 fish 版本了。

记住你访问过的目录，用几个字母就能跳回去。

## 安装

需要 fish 4.x。安装前请停用其他 `z` 插件。

### 手动安装（推荐）

```fish
git clone https://github.com/BoringApp/fish-z.git ~/.local/share/fish-z/plugin
```

在 `~/.config/fish/config.fish` 中加入这一行，然后打开新的终端：

```fish
source ~/.local/share/fish-z/plugin/fish-z.plugin.fish
```

以后更新时运行以下命令，再打开新的终端：

```fish
git -C ~/.local/share/fish-z/plugin pull --ff-only
```

### Fisher

已安装 [Fisher](https://github.com/jorgebucaran/fisher#installation) 的话：

```fish
fisher install BoringApp/fish-z
```

以后更新：

```fish
fisher update BoringApp/fish-z
```

## 使用

先用 `cd` 进入几个目录，fish-z 会自动记住它们。

```fish
z foo          # 跳到最匹配的目录
z foo bar      # 按顺序匹配多个关键词
z -c foo       # 只搜索当前目录下面
z -l foo       # 列出匹配目录及分数
```

按 **Tab** 补全匹配的目录。默认使用智能大小写：全小写查询忽略大小写，包含大写字母时严格匹配。

更多命令可运行 `z -h` 查看，高级选项见[参考文档](docs/reference.zh-CN.md)。

## Benchmark

在 Apple Silicon Mac 上使用 1,000 条目录记录，测量查询和补全耗时。
环境为 fish 4.9.3、zsh 5.9、zsh-z v2.0.1。
每组连续调用三次，共测五组取中位数，不包含 shell 启动时间。

| 操作 | fish-z | zsh-z |
| --- | ---: | ---: |
| 只匹配一个目录的查询 | 15.77 ms | 40.45 ms |
| 匹配全部目录的查询 | 104.89 ms | 43.54 ms |
| 生成全部补全候选 | 107.10 ms | 51.60 ms |

[测速脚本及运行方式](tests/benchmark_fish_z.py)。

## 致谢

由 [BoringApp](https://github.com/BoringApp) 维护，基于
[Alexandros Kozak 的 zsh-z](https://github.com/agkozak/zsh-z) 和
[rupa/z](https://github.com/rupa/z)。
采用 [MIT License](LICENSE)，保留上游版权声明。
