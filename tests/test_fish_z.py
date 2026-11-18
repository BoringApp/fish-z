"""Behavior and transaction tests. No third-party test dependencies."""
import concurrent.futures
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
FISH = shutil.which("fish")
REFERENCE = os.environ.get("ZSH_Z_REFERENCE")


class FishZTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fish-z-test-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.data = self.home / "data"
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("FISHZ_", "ZSHZ_", "_Z_")) and k != "fish_private_mode"}
        self.env.update(HOME=str(self.home), FISHZ_DATA=str(self.data),
                        XDG_CONFIG_HOME=str(self.home / "config"),
                        XDG_DATA_HOME=str(self.home / "share"),
                        FISHZ_TEST_PLUGIN=str(ROOT / "fish-z.plugin.fish"),
                        TERM="xterm-256color")
        self.now = int(time.time()) - 5

    def run_fish(self, script, *args, cwd=None, interactive=False, env=None):
        command = [FISH, "--no-config"]
        if interactive:
            command.append("--interactive")
        # Some fish builds start --no-config shells in private mode. This is a
        # disposable Home; privacy itself is exercised explicitly in its test.
        command += ["-c", 'set -g fish_private_mode 0; source "$FISHZ_TEST_PLUGIN"; ' + script, "--", *map(str, args)]
        return subprocess.run(command, env=self.env | (env or {}),
                              cwd=cwd or self.home, text=True, capture_output=True,
                              timeout=15)

    def z(self, *args, **kwargs):
        return self.run_fish("fishz $argv", *args, **kwargs)

    def directory(self, name):
        path = self.home / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def seed(self, *rows):
        self.data.write_text("".join(f"{path}|{rank}|{stamp}\n"
                                     for path, rank, stamp in rows))

    def rows(self):
        if not self.data.exists():
            return {}
        return {parts[0]: (float(parts[1]), int(parts[2]))
                for line in self.data.read_text().splitlines()
                if len(parts := line.split("|")) == 3}

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stderr, "")

    def test_syntax(self):
        for file in ROOT.rglob("*.fish"):
            with self.subTest(file=file.name):
                self.assert_ok(subprocess.run([FISH, "-N", "-n", str(file)],
                                              capture_output=True, text=True))

    def test_add_and_increment(self):
        path = self.directory("project")
        for visit in range(3):
            if visit == 1:
                self.data.chmod(0o644)
            self.assert_ok(self.z("--add", path))
        self.assertEqual(self.rows()[str(path)][0], 3)
        self.assertEqual(self.data.stat().st_mode & 0o777, 0o600)
        self.assertFalse(Path(str(self.data) + ".lock.d").exists())

    def test_special_paths_round_trip_and_literal_delete(self):
        for name in ["project.v1", "projectXv1", "a [b] ($cash) `x`", "中文 目录", r"back\slash", "-dash"]:
            path = self.directory(name)
            self.assert_ok(self.z("--add", path))
            self.assertIn(str(path), self.rows())
        self.assert_ok(self.z("-x", self.home / "project.v1"))
        self.assertNotIn(str(self.home / "project.v1"), self.rows())
        self.assertIn(str(self.home / "projectXv1"), self.rows())
        self.assertFalse(Path(str(self.data) + "-e").exists())

    def test_rank_recency_and_frecency(self):
        a, b = self.directory("old-project"), self.directory("new-project")
        self.seed((a, 100, self.now - 864000), (b, 10, self.now))
        for options, expected in [(["-er"], a), (["-et"], b), (["-e"], b)]:
            with self.subTest(options=options):
                r = self.z(*options, "project")
                self.assert_ok(r)
                self.assertEqual(r.stdout.strip(), str(expected))

    def test_case_modes(self):
        a, b = self.directory("project"), self.directory("PROJECT")
        self.seed((a, 1, self.now), (b, 20, self.now))
        for mode, query, expected in [(None, "project", b), ("", "project", b),
                                      ("ignore", "project", b), ("ignore", "ProJECT", b),
                                      ("smart", "project", b), ("smart", "PROJECT", b),
                                      ("fallback", "project", a), ("fallback", "ProJECT", b)]:
            with self.subTest(mode=mode, query=query):
                env = {} if mode is None else {"FISHZ_CASE": mode}
                r = self.z("-er", query, env=env)
                self.assert_ok(r)
                self.assertEqual(r.stdout.strip(), str(expected))
        for mode in (None, "", "smart"):
            env = {} if mode is None else {"FISHZ_CASE": mode}
            self.assertNotEqual(self.z("-e", "ProJECT", env=env).returncode, 0)

    def test_default_smart_case_jump_and_completion(self):
        lower, upper = self.directory("workspace/odps"), self.directory("workspace/DPScope")
        self.seed((lower, 18, self.now), (upper, 106, self.now))
        result = self.run_fish('fishz dps; and pwd')
        self.assert_ok(result)
        self.assertEqual(result.stdout.strip(), str(upper))
        self.assertEqual(self.z("--complete", "dps").stdout.splitlines(), [str(upper), str(lower)])
        self.assertEqual(self.z("--complete", "DPS").stdout.splitlines(), [str(upper)])
        self.assertEqual(self.z("-e", "dps", env={"FISHZ_CASE": "fallback"}).stdout.strip(), str(lower))

    def test_ordered_terms(self):
        a, b = self.directory("alpha/omega"), self.directory("omega/alpha")
        self.seed((a, 1, self.now), (b, 100, self.now))
        self.assertEqual(self.z("-e", "alpha", "omega").stdout.strip(), str(a))

    def test_exact_name_precedes_descendants_and_longer_names(self):
        a, b = self.directory("code"), self.directory("code/child")
        self.seed((a, 1, self.now), (b, 30, self.now))
        self.assertEqual(self.z("-er", "code").stdout.strip(), str(a))
        c = self.directory("codebase")
        self.seed((a, 1, self.now), (c, 30, self.now))
        self.assertEqual(self.z("-er", "code").stdout.strip(), str(a))

    def test_name_priority_overrides_frequency_and_recency(self):
        exact = self.directory("exact/dps")
        prefix = self.directory("prefix/DPScope")
        substring = self.directory("substring/odps")
        ancestor = self.directory("ancestor/dps/scripts")
        paths = [exact, prefix, substring, ancestor]
        rows = [(path, 10 ** i, self.now - (3 - i) * 86400)
                for i, path in enumerate(paths)]
        for start in range(len(paths)):
            with self.subTest(best=paths[start].name):
                self.seed(*rows[start:])
                before = self.data.read_bytes()
                for options in ("-e", "-er", "-et"):
                    result = self.z(options, "dps")
                    self.assert_ok(result)
                    self.assertEqual(result.stdout.strip(), str(paths[start]))
                for options in ([], ["-r"], ["-t"]):
                    result = self.z("--complete", *options, "dps")
                    self.assert_ok(result)
                    self.assertEqual(result.stdout.splitlines(), list(map(str, paths[start:])))
                for options, expected in [("-lr", list(reversed(paths[start:]))),
                                          ("-lt", paths[start:])]:
                    result = self.z(options, "dps")
                    self.assert_ok(result)
                    self.assertEqual([line.split(maxsplit=1)[1] for line in result.stdout.splitlines()],
                                     list(map(str, expected)))
                self.assertEqual(self.data.read_bytes(), before)

    def test_recent_substring_does_not_beat_an_older_prefix(self):
        lower, upper = self.directory("workspace/odps"), self.directory("workspace/DPScope")
        self.seed((lower, 32, self.now), (upper, 107, self.now - 20 * 3600))
        result = self.run_fish('fishz dps; and pwd')
        self.assert_ok(result)
        self.assertEqual(result.stdout.strip(), str(upper))
        result = self.run_fish("complete -C 'z dps'", interactive=True)
        self.assert_ok(result)
        self.assertEqual([line.split("\t")[0] for line in result.stdout.splitlines()],
                         [str(upper), str(lower)])

    def test_same_name_priority_uses_scores_without_ancestor_override(self):
        parent = self.directory("DPScope")
        child = self.directory("DPScope/DPS-other")
        self.seed((parent, 100, self.now - 864000), (child, 10, self.now))
        for options, expected in [("-er", parent), ("-et", child), ("-e", child)]:
            result = self.z(options, "dps")
            self.assert_ok(result)
            self.assertEqual(result.stdout.strip(), str(expected))
        exact = self.directory("DPScope/dps")
        self.seed((parent, 10000, self.now), (exact, 1, self.now - 86400))
        self.assertEqual(self.z("-e", "dps").stdout.strip(), str(exact))

    def test_final_term_grades_names_after_ordered_path_matching(self):
        exact, prefix, substring, ancestor = (self.directory(name) for name in
            ("work/dps", "work/DPScope", "work/odps", "work/dps/scripts"))
        outside = self.directory("elsewhere/dps")
        paths = [exact, prefix, substring, ancestor]
        self.seed(*[(path, 10 ** i, self.now) for i, path in enumerate(paths)],
                  (outside, 10000, self.now))
        for terms in [("work", "dps"), ("work", "dps", "")]:
            result = self.z("--complete", *terms)
            self.assert_ok(result)
            self.assertEqual(result.stdout.splitlines(), list(map(str, paths)))
        self.assertEqual(self.z("-e", "work", "DPS").stdout.strip(), str(prefix))
        # Slash-containing terms grade their final component while still
        # requiring the entire path expression to match.
        self.assertEqual(self.z("--complete", "work/dps").stdout.splitlines(),
                         [str(exact), str(prefix), str(ancestor)])

    def test_name_priority_handles_literal_characters_and_wildcards(self):
        for name in ("a.[b]", "中文 目录", r"back\slash", "a ($cash)"):
            with self.subTest(name=name):
                paths = [self.directory("literal/" + part) for part in
                         (name, name + "-more", "other-" + name, name + "/child")]
                self.seed(*[(path, 10 ** i, self.now) for i, path in enumerate(paths)])
                result = self.z("--complete", name)
                self.assert_ok(result)
                self.assertEqual(result.stdout.splitlines(), list(map(str, paths)))
        exact, prefix, substring, ancestor = (self.directory(name) for name in
            ("glob/dps", "glob/DPScope", "glob/odps", "glob/dps/scripts"))
        paths = [exact, prefix, substring, ancestor]
        self.seed(*[(path, 10 ** i, self.now) for i, path in enumerate(paths)])
        self.assertEqual(self.z("--complete", "d?s").stdout.splitlines(), list(map(str, paths)))
        self.assertEqual(self.z("--complete", "*dps").stdout.splitlines(),
                         [str(substring), str(exact), str(prefix), str(ancestor)])

    def test_name_priority_keeps_directory_filters_and_trailing_slashes(self):
        root = self.directory("work")
        prefix = self.directory("work/DPScope")
        missing = self.home / "work/dps"
        outside = self.directory("elsewhere/dps")
        self.seed((prefix, 1, self.now), (missing, 100, self.now), (outside, 1000, self.now))
        self.assertEqual(self.z("-ec", "dps", cwd=root).stdout.strip(), str(prefix))
        self.assertEqual(self.z("-ec", "dps", cwd=root,
                               env={"FISHZ_KEEP_DIRS": str(missing)}).stdout.strip(), str(missing))
        missing.mkdir()
        child = self.directory("work/dps/child")
        self.seed((str(missing) + "/", 1, self.now), (child, 100, self.now))
        result = self.z("--complete", "dps/", env={"FISHZ_TRAILING_SLASH": "1"})
        self.assert_ok(result)
        self.assertEqual(result.stdout.splitlines(), [str(missing) + "/", str(child)])

    def test_uncommon_keeps_deepest_occurrence(self):
        path = self.directory("code/foo/code/bar")
        self.seed((path, 20, self.now))
        r = self.z("-e", "code", env={"FISHZ_UNCOMMON": "1"})
        self.assert_ok(r)
        self.assertEqual(r.stdout.strip(), str(path.parent))

    def test_c_restricts_subtrees_and_root(self):
        root = self.directory("work")
        inside, outside = self.directory("work/project"), self.directory("workshop/project")
        self.seed((inside, 1, self.now), (outside, 50, self.now))
        self.assertEqual(self.z("-ec", "project", cwd=root).stdout.strip(), str(inside))
        self.assertEqual(self.z("-erc", "project", cwd="/").stdout.strip(), str(outside))

    def test_bare_z_lists_and_does_not_cd(self):
        path = self.directory("project")
        self.seed((path, 1, self.now))
        r = self.run_fish('fishz; printf "CWD=%s\\n" "$PWD"')
        self.assert_ok(r)
        self.assertIn(str(path), r.stdout)
        self.assertIn(f"CWD={self.home}", r.stdout)

    def test_unknown_and_conflicting_options_do_not_cd(self):
        path = self.directory("project")
        self.seed((path, 1, self.now))
        for args in [["--not-valid"], ["-rt"], ["-R"], ["--add", "-x", str(path)]]:
            r = self.run_fish('fishz $argv; printf "STATUS=%s CWD=%s\\n" $status "$PWD"', *args)
            self.assertIn(f"STATUS=2 CWD={self.home}", r.stdout)

    def test_leading_hyphen_pattern(self):
        path = self.directory("-dash")
        self.seed((path, 1, self.now))
        self.assertEqual(self.z("-e", "--", "-dash").stdout.strip(), str(path))
        self.assertNotEqual(self.z("-e", "--", "-missing").returncode, 0)

    def test_direct_paths_and_relative_fallback(self):
        path = self.directory("project")
        for arg in [str(path), "project"]:
            r = self.run_fish('fishz $argv; pwd', arg)
            self.assert_ok(r)
            self.assertEqual(r.stdout.strip(), str(path))
        self.assertNotEqual(self.z("-e", "project").returncode, 0)

    def test_remove_missing_and_recursive_boundaries(self):
        a = self.directory("work")
        b, c = self.directory("work/sub"), self.directory("workshop")
        missing = self.home / "gone"
        self.seed((a, 1, self.now), (b, 1, self.now), (c, 1, self.now), (missing, 1, self.now))
        self.assert_ok(self.z("-x", missing))
        self.assert_ok(self.z("-xR", a))
        self.assertEqual(set(self.rows()), {str(c)})

    def test_remove_absent_returns_failure(self):
        self.assertEqual(self.z("-x", self.home / "missing").returncode, 1)

    def test_home_private_and_excluded_are_not_recorded(self):
        self.assert_ok(self.z("--add", self.home))
        p = self.directory("work/project")
        self.assert_ok(self.z("--add", p, env={"FISHZ_EXCLUDE_DIRS": str(p.parent)}))
        self.assert_ok(self.run_fish('set -g fish_private_mode 1; fishz --add $argv', p))
        self.assertEqual(self.rows(), {})
        other = self.directory("workshop")
        self.assert_ok(self.z("--add", other, env={"FISHZ_EXCLUDE_DIRS": str(p.parent)}))
        self.assertIn(str(other), self.rows())

    def test_missing_directories_pruned_except_keep(self):
        missing, kept, existing = self.home / "missing", self.home / "offline/project", self.directory("active")
        self.seed((missing, 2, self.now), (kept, 3, self.now))
        self.assert_ok(self.z("--add", existing, env={"FISHZ_KEEP_DIRS": str(kept.parent)}))
        self.assertEqual(set(self.rows()), {str(kept), str(existing)})
        self.assertEqual(self.z("-e", "offline", env={"FISHZ_KEEP_DIRS": str(kept.parent)}).stdout.strip(), str(kept))

    def test_malformed_records_are_ignored(self):
        p = self.directory("project")
        self.data.write_text(f"bad\n{p}|oops|123\n{p}|2|{self.now}\n/extra|1|2|3\n")
        self.assertEqual(self.z("-e", "project").stdout.strip(), str(p))
        self.assert_ok(self.z("--add", p))
        self.assertEqual(self.rows()[str(p)][0], 3)
        self.assertEqual(len(self.data.read_text().splitlines()), 1)

    def test_duplicate_queries_keep_first_record_and_distinct_literal_paths(self):
        a, b, upper = (self.directory(name) for name in ("item1", "item01", "ITEM1"))
        trailing = str(a) + "/"
        self.seed((a, 0, self.now), (b, 3, self.now), (upper, 4, self.now),
                  (a, 100, self.now), (trailing, 2, self.now))
        result = self.z("--complete", "-r")
        self.assert_ok(result)
        self.assertEqual(result.stdout.splitlines(), [str(upper), str(b), trailing, str(a)])
        result = self.z("-lr")
        self.assert_ok(result)
        self.assertNotIn(str(a), [line.split(maxsplit=1)[1] for line in result.stdout.splitlines()])

    def test_duplicate_writes_keep_last_valid_values_and_first_path_order(self):
        a, b, c = (self.directory(name) for name in ("a-b", "a_2D_b", "中文 [x]"))
        self.seed((a, 2, self.now - 10), (b, 3, self.now), (a, 7, self.now),
                  (c, 4, self.now), (b, .5, self.now))
        self.assert_ok(self.z("--add", a))
        self.assertEqual([line.split("|")[0] for line in self.data.read_text().splitlines()],
                         [str(a), str(b), str(c)])
        self.assertEqual(self.rows()[str(a)][0], 8)
        self.assertEqual(self.rows()[str(b)][0], 3)
        # Removal does not prune low ranks; the last duplicate still wins there.
        self.seed((a, 2, self.now), (b, 3, self.now), (b, .5, self.now))
        self.assert_ok(self.z("-x", a))
        self.assertEqual(self.rows()[str(b)][0], .5)

    def test_case_fallback_after_directory_and_zero_score_filters(self):
        missing, upper = self.home / "offline/project", self.directory("online/PROJECT")
        env = {"FISHZ_CASE": "fallback"}
        self.seed((missing, 1, self.now), (upper, 3, self.now))
        self.assertEqual(self.z("-er", "project", env=env).stdout.strip(), str(upper))
        self.assertEqual(self.z("-er", "project", env=env | {"FISHZ_KEEP_DIRS": str(missing)}).stdout.strip(), str(missing))
        missing.mkdir(parents=True)
        self.seed((missing, 0, self.now), (upper, 3, self.now))
        result = self.z("-lr", "project", env=env)
        self.assert_ok(result)
        self.assertEqual(result.stdout.split(maxsplit=1)[1].strip(), str(upper))
        self.assertEqual(self.z("-er", "project", env=env).stdout.strip(), str(missing))

    def test_batch_matching_never_searches_rank_or_timestamp(self):
        path = self.directory("project")
        self.seed((path, 9876543210, 9876543210))
        for query in ("9876543210", "project*9876543210", "project|*"):
            with self.subTest(query=query):
                result = self.z("-e", query)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")

    def test_subtree_filter_preserves_trailing_slash_records(self):
        root = self.directory("work [x]")
        child = self.directory("work [x]/child")
        outside = self.directory("work [x]shop/child")
        trailing = str(root) + "/"
        self.seed((root, 100, self.now), (trailing, 3, self.now),
                  (child, 2, self.now), (outside, 200, self.now))
        result = self.z("--complete", "-rc", cwd=root)
        self.assert_ok(result)
        self.assertEqual(result.stdout.splitlines(), [trailing, str(child)])

    def test_fractional_score_sort_keys_and_ties(self):
        paths = [self.directory(name) for name in ("item1", "item2", "item10", "ITEM")]
        self.seed(*[(path, rank, self.now) for path, rank in
                    zip(paths, ("0.29", "0.2899999", "0.2800001", "0.28"))])
        # Preserve floor(rank * 100), including its floating-point boundary,
        # followed by the existing natural ordering of score and path ties.
        result = self.z("--complete", "-r")
        self.assert_ok(result)
        self.assertEqual(result.stdout.splitlines(), [str(paths[i]) for i in (1, 2, 0, 3)])

    def test_aging(self):
        a, b = self.directory("one"), self.directory("two")
        self.seed((a, 10, self.now), (b, .5, self.now))
        self.assert_ok(self.z("--add", a, env={"FISHZ_MAX_SCORE": "5"}))
        self.assertAlmostEqual(self.rows()[str(a)][0], 10.89)
        self.assertNotIn(str(b), self.rows())

    def test_symlink_database_is_preserved(self):
        actual = self.home / "real-data"
        self.data.symlink_to(actual)
        p = self.directory("project")
        self.assert_ok(self.z("--add", p))
        self.assertTrue(self.data.is_symlink())
        self.assertTrue(actual.exists())
        self.assertIn(str(p), self.rows())

    def test_logical_and_physical_directory_paths(self):
        actual = self.directory("actual")
        link = self.home / "alias"
        link.symlink_to(actual, target_is_directory=True)
        self.assert_ok(self.z("--add", link))
        self.assertIn(str(actual), self.rows())
        self.assert_ok(self.z("--add", link, env={"FISHZ_NO_RESOLVE_SYMLINKS": "1"}))
        self.assertIn(str(link), self.rows())

    def test_tilde_echo_and_custom_cd(self):
        path = self.directory("project")
        self.seed((path, 1, self.now))
        self.assertEqual(self.z("-e", "project", env={"FISHZ_TILDE": "1"}).stdout.strip(), "~/project")
        r = self.run_fish('function go; builtin cd -- $argv; end; set -g FISHZ_CD go; set -g FISHZ_ECHO 1; fishz project')
        self.assert_ok(r)
        self.assertEqual(r.stdout.strip(), str(path))

    def test_trailing_slash(self):
        path = self.directory("project")
        self.seed((path, 1, self.now))
        self.assertNotEqual(self.z("-e", "project/").returncode, 0)
        self.assertEqual(self.z("-e", "project/", env={"FISHZ_TRAILING_SLASH": "1"}).stdout.strip(), str(path))
        child = self.directory("project/child")
        self.seed((child, 2, self.now))
        r = self.z("-e", "project/", env={"FISHZ_TRAILING_SLASH": "1", "FISHZ_UNCOMMON": "1"})
        self.assertEqual(r.stdout.strip(), str(path))

    def test_completion_sort_and_mutation_options(self):
        a, b = self.directory("alpha"), self.directory("beta")
        self.seed((a, 1, self.now), (b, 5, self.now - 100))
        before = self.data.read_bytes()
        self.assertEqual(self.z("--complete", "-r").stdout.splitlines(), [str(b), str(a)])
        self.assertEqual(self.z("--complete", "-t").stdout.splitlines(), [str(a), str(b)])
        self.assertEqual(self.z("--complete", env={"FISHZ_COMPLETION": "legacy"}).stdout.splitlines(), [str(a), str(b)])
        self.z("--complete", "--add", a)
        self.z("--complete", "-x", a)
        self.assertEqual(self.data.read_bytes(), before)

    def test_fish_completion_uses_tokens_options_and_spaces(self):
        a, b = self.directory("code/fish space"), self.directory("code/fish-other")
        self.seed((a, 10, self.now), (b, 1, self.now))
        r = self.run_fish("complete -C 'z -r code fish'", interactive=True)
        self.assert_ok(r)
        candidates = [line.split("\t")[0] for line in r.stdout.splitlines()]
        self.assertEqual(candidates, [str(a), str(b)])

    def test_read_only_commands_do_not_create_database(self):
        self.assertNotEqual(self.z("-l").returncode, 0)
        self.assertFalse(self.data.exists())

    def test_lock_timeout_preserves_database(self):
        p = self.directory("project")
        self.seed((p, 1, self.now))
        before = self.data.read_bytes()
        lock = Path(str(self.data) + ".lock.d")
        lock.mkdir()
        r = self.z("--add", p, env={"FISHZ_LOCK_TIMEOUT": "0"})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.data.read_bytes(), before)
        self.assertTrue(lock.exists())

    def test_failed_rename_preserves_history_and_cleans_temp(self):
        p = self.directory("project")
        self.seed((p, 1, self.now))
        before = self.data.read_bytes()
        bindir = self.directory("bin")
        mv = bindir / "mv"
        mv.write_text("#!/bin/sh\nexit 1\n")
        mv.chmod(0o755)
        r = self.z("--add", p, env={"PATH": str(bindir) + os.pathsep + self.env["PATH"]})
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.data.read_bytes(), before)
        self.assertEqual(list(self.home.glob("data.*")), [])

    def test_concurrent_writes_keep_all_visits(self):
        p = self.directory("project")
        def add(_):
            return self.z("--add", p, env={"FISHZ_LOCK_TIMEOUT": "5"})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for result in pool.map(add, range(24)):
                self.assert_ok(result)
        self.assertEqual(self.rows()[str(p)][0], 24)
        self.assertEqual(list(self.home.glob("data.*")), [])

    def test_background_add_then_remove_stays_removed(self):
        p = self.directory("project")
        r = self.run_fish('emit fish_prompt; fishz -x; emit fish_prompt; sleep 0.1',
                          cwd=p, interactive=True)
        self.assert_ok(r)
        self.assertNotIn(str(p), self.rows())

    def test_resourcing_does_not_duplicate_hook(self):
        p = self.directory("project")
        r = self.run_fish('source "$FISHZ_TEST_PLUGIN"; emit fish_prompt; sleep 0.2',
                          cwd=p, interactive=True)
        self.assert_ok(r)
        self.assertEqual(self.rows()[str(p)][0], 1)

    def test_custom_command_can_be_fishz(self):
        p = self.directory("project")
        self.seed((p, 1, self.now))
        r = self.run_fish('fishz -e project', interactive=True,
                          env={"FISHZ_CMD": "fishz"})
        self.assert_ok(r)
        self.assertEqual(r.stdout.strip(), str(p))

    def test_termination_releases_transaction_lock(self):
        p = self.directory("project")
        self.seed(*[(self.home / f"offline/item{i}", 2, self.now) for i in range(2000)])
        before = self.data.read_bytes()
        command = [FISH, "-N", "-c",
                   'set -g fish_private_mode 0; source "$FISHZ_TEST_PLUGIN"; fishz --add "$argv[1]"',
                   "--", str(p)]
        env = self.env | {"FISHZ_KEEP_DIRS": str(self.home / "offline")}
        process = subprocess.Popen(command, cwd=self.home, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        lock = Path(str(self.data) + ".lock.d")
        try:
            deadline = time.monotonic() + 5
            while not (lock / "owner").exists() and time.monotonic() < deadline:
                time.sleep(.005)
            writer = int((lock / "owner").read_text().strip())
            os.kill(writer, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=10)
            self.assertNotEqual(process.returncode, 0, stdout + stderr)
            self.assertFalse(lock.exists(), stderr)
            self.assertEqual(self.data.read_bytes(), before)
            self.assertEqual(list(self.home.glob("data.*")), [])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    @unittest.skipUnless(REFERENCE, "set ZSH_Z_REFERENCE for upstream differential tests")
    def test_upstream_search_parity(self):
        a, b, c = self.directory("code/alpha"), self.directory("code/beta"), self.directory("CODE/gamma")
        self.seed((a, 10, self.now - 86400), (b, 2, self.now), (c, 100, self.now - 999999))
        for args in [["-e", "code"], ["-er", "code"], ["-et", "code"], ["-e", "CODE"], ["-e", "code", "beta"]]:
            for mode, upstream_mode in [(None, "smart"), ("", "smart"), ("ignore", "ignore"),
                                        ("smart", "smart"), ("fallback", "")]:
                with self.subTest(args=args, mode=mode):
                    env = self.env | {"ZSHZ_DATA": str(self.data), "ZSHZ_CASE": upstream_mode}
                    reference = subprocess.run(["zsh", "-f", "-c", 'source "$1"; shift; zshz "$@"',
                                                "ref", REFERENCE, *args], env=env, cwd=self.home,
                                               text=True, capture_output=True, timeout=10)
                    actual = self.z(*args, env={} if mode is None else {"FISHZ_CASE": mode})
                    self.assertEqual(actual.stdout, reference.stdout, reference.stderr)
                    self.assertEqual(actual.returncode, reference.returncode)

    @unittest.skipUnless(REFERENCE, "set ZSH_Z_REFERENCE for upstream differential tests")
    def test_upstream_uncommon_parity(self):
        path = self.directory("code/foo/code/bar/trailer")
        self.seed((path, 20, self.now))
        for query in [["code"], ["foo", "bar"], ["co*bar"], ["CODE"], ["co?e"]]:
            with self.subTest(query=query):
                env = self.env | {"ZSHZ_DATA": str(self.data), "ZSHZ_UNCOMMON": "1", "ZSHZ_CASE": "smart"}
                reference = subprocess.run(["zsh", "-f", "-c", 'source "$1"; shift; zshz -e "$@"',
                                            "ref", REFERENCE, *query], env=env, cwd=self.home,
                                           text=True, capture_output=True, timeout=10)
                actual = self.z("-e", *query, env={"FISHZ_UNCOMMON": "1"})
                self.assertEqual(actual.stdout, reference.stdout, reference.stderr)
                self.assertEqual(actual.returncode, reference.returncode)


if __name__ == "__main__":
    unittest.main()
