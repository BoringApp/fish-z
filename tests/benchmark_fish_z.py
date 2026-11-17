"""Compare warm-shell latency using disposable, identical history databases.

python3 tests/benchmark_fish_z.py --reference /path/to/zsh-z.plugin.zsh \
    --baseline /path/to/previous/fish-z

No user configuration or history is loaded. Times include the actual command,
but exclude parent-shell startup and fixture resets. record_sync measures a
foreground --add (including its worker), not asynchronous prompt latency.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import selectors
import shutil
import statistics
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = {
    "search_one": "-e project-0001",
    "search_all": "-e project",
    "complete_all": "--complete project",
    "record_sync": '--add "$BENCH_TARGET"',
}


class Shell:
    def __init__(self, binary, kind, env, cwd):
        self.kind = kind
        self.errors = tempfile.TemporaryFile()
        if kind == "fish":
            command = [binary, "--no-config", "-c",
                       'while read -l bench_cmd; eval "$bench_cmd"; '
                       'printf "__BENCH_DONE__\\n"; end']
        else:
            command = [binary, "-f", "-c",
                       'while IFS= read -r bench_cmd; do eval "$bench_cmd"; '
                       'printf "__BENCH_DONE__\\n"; done']
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.errors,
                                        env=env, cwd=cwd, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)

    def run(self, command):
        start = time.perf_counter()
        self.process.stdin.write((command + "\n").encode())
        output = b""
        deadline = start + 60
        while b"__BENCH_DONE__\n" not in output:
            if not self.selector.select(max(0, deadline - time.perf_counter())):
                raise RuntimeError(f"{self.kind} benchmark timed out")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                self.errors.seek(0)
                raise RuntimeError(self.errors.read().decode(errors="replace"))
            output += chunk
        return time.perf_counter() - start

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.selector.close()
        self.process.stdout.close()
        self.errors.seek(0)
        error = self.errors.read().decode(errors="replace")
        self.errors.close()
        if error:
            raise RuntimeError(error)


def benchmark(args):
    fish, zsh = shutil.which("fish"), shutil.which("zsh")
    if not fish or not zsh:
        raise SystemExit("Both fish and zsh must be installed")
    sources = {"fish": ("fish", ROOT / "fish-z.plugin.fish"),
               "zsh": ("zsh", args.reference.resolve())}
    if args.baseline:
        sources["before"] = ("fish", args.baseline.resolve() / "fish-z.plugin.fish")
    for _, source in sources.values():
        if not source.is_file():
            raise SystemExit(f"Missing plugin: {source}")
    print(json.dumps({"platform": platform.platform(),
                      "fish": subprocess.check_output([fish, "--version"], text=True).strip(),
                      "zsh": subprocess.check_output([zsh, "--version"], text=True).strip(),
                      "trials": args.trials, "batch": args.batch}), flush=True)
    with tempfile.TemporaryDirectory(prefix="fish-z-benchmark-") as temporary:
        root = Path(temporary).resolve()
        home = root / "home"
        home.mkdir()
        for size in args.sizes:
            base = root / str(size)
            paths = [base / f"group{i % 10}" / f"project-{i:04d}" for i in range(size)]
            for path in paths:
                path.mkdir(parents=True)
            now = int(time.time()) - 10
            rows = "".join(f"{path}|{1 + i % 20}|{now - i % 72 * 3600}\n"
                           for i, path in enumerate(paths))
            databases = {name: base / (name + ".data") for name in sources}
            shells = {}
            try:
                for name, (kind, plugin) in sources.items():
                    databases[name].write_text(rows)
                    env = {k: v for k, v in os.environ.items()
                           if not k.startswith(("FISHZ_", "ZSHZ_", "_Z_"))
                           and k != "fish_private_mode"}
                    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"),
                               XDG_DATA_HOME=str(home / "share"), LC_ALL="C",
                               FISHZ_DATA=str(databases[name]), ZSHZ_DATA=str(databases[name]),
                               BENCH_PLUGIN=str(plugin), BENCH_TARGET=str(paths[0]))
                    shell = Shell(fish if kind == "fish" else zsh, kind, env, home)
                    shells[name] = shell
                    shell.run(('set -g fish_private_mode 0; ' if kind == "fish" else '')
                              + 'source "$BENCH_PLUGIN"')
                results = {}
                for operation, options in OPERATIONS.items():
                    commands = {
                        name: ("fishz" if shell.kind == "fish" else "zshz")
                        + " " + options + " >/dev/null"
                        + ("; or exit 10" if shell.kind == "fish" else " || exit 10")
                        for name, shell in shells.items()
                    }
                    for name, shell in shells.items():
                        shell.run(commands[name])
                    samples = {name: [] for name in shells}
                    names = list(shells)
                    for trial in range(args.trials):
                        offset = trial % len(names)
                        for name in names[offset:] + names[:offset]:
                            if operation == "record_sync":
                                databases[name].write_text(rows)
                            elapsed = shells[name].run("; ".join([commands[name]] * args.batch))
                            samples[name].append(elapsed * 1000 / args.batch)
                    results[operation] = {name: round(statistics.median(values), 2)
                                          for name, values in samples.items()}
                print(json.dumps({"entries": size, "median_ms_per_operation": results}), flush=True)
            finally:
                for shell in shells.values():
                    shell.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 200, 1000])
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--batch", type=int, default=3)
    arguments = parser.parse_args()
    if min(arguments.sizes) < 2 or min(arguments.trials, arguments.batch) < 1:
        parser.error("sizes must be >= 2; trials and batch must be positive")
    benchmark(arguments)
