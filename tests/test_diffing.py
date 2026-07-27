from grounded.diffing import parse_unified_diff


def test_new_file_line_numbers():
    diff = (
        "diff --git a/f.py b/f.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/f.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+alpha\n"
        "+beta\n"
        "+gamma\n"
    )
    parsed = parse_unified_diff(diff)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.path == "f.py" and f.is_new
    assert [(a.lineno, a.content) for a in f.added_lines] == [(1, "alpha"), (2, "beta"), (3, "gamma")]


def test_line_numbers_track_context_and_removals():
    diff = (
        "diff --git a/f.py b/f.py\n"
        "--- a/f.py\n"
        "+++ b/f.py\n"
        "@@ -10,4 +10,4 @@\n"
        " context_ten\n"
        "-removed_eleven\n"
        "+added_eleven\n"
        " context_twelve\n"
    )
    parsed = parse_unified_diff(diff)
    added = parsed.files[0].added_lines
    # new file: line 10 context, line 11 is the added line (removal doesn't advance new counter)
    assert [(a.lineno, a.content) for a in added] == [(11, "added_eleven")]


def test_rename_and_delete_flags():
    diff = (
        "diff --git a/old.py b/new.py\n"
        "similarity index 90%\n"
        "rename from old.py\n"
        "rename to new.py\n"
    )
    f = parse_unified_diff(diff).files[0]
    assert f.is_rename and f.path == "new.py" and f.old_path == "old.py"


def test_binary_file_recorded_not_crashed():
    diff = (
        "diff --git a/img.png b/img.png\n"
        "Binary files a/img.png and b/img.png differ\n"
    )
    f = parse_unified_diff(diff).files[0]
    assert f.is_binary and f.added_lines == []


def test_malformed_hunk_degrades():
    # A hunk with no preceding file header is recorded as an error, not raised.
    diff = "@@ this is not a real hunk header @@\n+something\n"
    parsed = parse_unified_diff(diff)
    assert parsed.files == []  # nothing parsed
    # tolerated: parser returned instead of raising


def test_multi_file_diff():
    diff = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,0 +1,1 @@\n+one\n"
        "diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n@@ -1,0 +1,1 @@\n+two\n"
    )
    parsed = parse_unified_diff(diff)
    assert [f.path for f in parsed.files] == ["a.py", "b.py"]
