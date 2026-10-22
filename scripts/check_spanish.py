#!/usr/bin/env python3
"""Spanish orthography guard (U16-P1a, BL-089): no unaccented Spanish word in the Spanish texts the product writes or shows.

It reads, without evaluating anything:
  - the producers: the string constants of data-pipeline/pipeline/**/*.py (read with ast) and the strings of its JSON files;
  - the frontend: the strings of frontend/src/**/*.ts(x) (a small TypeScript tokenizer) and the text of its JSX;
  - with --documents, the ``es`` values (and ``*_es`` values) of the committed JSON documents under data/derived/, and every
    bilingual object ``{en, es}`` whose ``es`` equals its ``en`` when the ``en`` has three words or more (U16-F1): a Spanish field
    that copies the English. scripts/check_spanish_copies.txt lists the copies that are right (``path :: text  # reason``; a
    line without a reason is a finding).
Frontend tests and generated files (*.test.ts(x), *.gen.ts) are not scanned.

A finding is (1) a word of scripts/check_spanish_words.txt written without its accent, in any text that is not an identifier,
a path or a URL, or (2) in a Spanish text, a word ending in -cion or -sion (the plurals need no accent). A Spanish text is the second
argument of t(en, es), a value under an ``es`` or ``*_es`` key, or any text whose function words are Spanish. A docstring is not
a text. A finding prints ``path:line: word -> fix`` and the exit code is 1. scripts/check_spanish_allow.txt lists the findings
that are right as written (``path :: word  # reason``); an entry that matches nothing is itself a finding.

Usage: check_spanish.py [--root DIR] [--documents] [--words FILE] [--allow FILE] [PATH ...]
CI runs it without --documents (the code); the release runs it with --documents after the re-bake. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORD = re.compile(r"[A-Za-zÀ-ÿ]+")
ENDING = re.compile(r"[cs]ion$", re.IGNORECASE)
ES_FUNCTION = frozenset("de la los las del que con por para una se sin entre más al su sus lo les esta este estos estas cuando "
                        "donde porque según también pero ya hay fue ser está están cada sobre desde hasta el qué cómo no y".split())
ES_ONLY = ES_FUNCTION - {"y", "no", "el", "se", "una", "este", "esta"}
EN_FUNCTION = frozenset("the of and to is are for with that this from by on as be at it its or not an which when where what how".split())
HELPERS = frozenset({"t", "_t", "T", "txt", "text", "tr"})
CODE_ROOTS = ("data-pipeline/pipeline", "data-pipeline/config")
UI_ROOT = "frontend/src"
DOC_ROOT = "data/derived"


def strip_accents(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


def load_words(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            key, fix = line.split()
            pairs[key] = fix
    return pairs


def load_allow(path: Path | None) -> dict[tuple[str, str], bool]:
    allow: dict[tuple[str, str], bool] = {}
    if path and path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                where, word = (part.strip() for part in line.split("::", 1))
                allow[(where, word.lower())] = False
    return allow


def identifier_like(text: str) -> bool:
    """A key, a path, a URL, a file name or a code token: no whitespace and a code character in it."""
    if any(c.isspace() for c in text):
        return False
    return bool(re.search(r"[_/.:#=0-9]|[a-z][A-Z]", text)) or bool(re.fullmatch(r"[a-z]+(-[a-z]+)+", text))


def spanish_text(text: str) -> bool:
    words = [w.lower() for w in WORD.findall(text)]
    es = sum(1 for w in words if w in ES_ONLY)
    en = sum(1 for w in words if w in EN_FUNCTION)
    if any(c in text for c in "áéíóúñ¿¡") and en == 0:
        return True
    return es >= 1 and es > en


def english_copy(text: str) -> bool:
    """An ``es`` slot that holds the English text on purpose (a quotation kept in English): English function words, no Spanish."""
    words = [w.lower() for w in WORD.findall(text)]
    en = sum(1 for w in words if w in EN_FUNCTION)
    return en >= 2 and en > 2 * sum(1 for w in words if w in ES_ONLY)


def fix_case(word: str, fix: str) -> str:
    if len(word) > 1 and word.isupper():
        return fix.upper()
    if word[0].isupper():
        return fix[0].upper() + fix[1:]
    return fix


def check_text(text: str, certain: bool, words: dict[str, str]) -> list[tuple[str, str]]:
    """The (word, fix) findings of one text; ``certain`` marks a text known to be Spanish by its position."""
    text = re.sub(r"\{[^{}]*\}", " ", text)    # a format placeholder is code, not text
    if not text.strip() or identifier_like(text):
        return []
    spanish = (certain and not english_copy(text)) or spanish_text(text)
    out = []
    for m in WORD.finditer(text):
        word = m.group(0)
        if any(ord(c) > 127 for c in word):
            continue
        low = word.lower()
        if low in words:
            out.append((word, fix_case(word, words[low])))
        elif spanish and ENDING.search(low) and len(low) > 5 and not word.isupper():
            out.append((word, fix_case(word, re.sub(r"([cs])ion$", lambda k: k.group(1) + "ión", low))))
    return out


# --- Python ---------------------------------------------------------------------------------------------------------------

def _py_certain(tree: ast.AST) -> set[int]:
    """ids of the string nodes that sit in a Spanish position: an ``es`` value or the arguments after the first of t()."""
    marked: set[int] = set()

    def mark(node: ast.AST) -> None:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                marked.add(id(sub))

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and (k.value == "es" or k.value.endswith("_es")):
                    mark(v)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
            if name in HELPERS:
                for arg in node.args[1:]:
                    mark(arg)
            for kw in node.keywords:
                if kw.arg and (kw.arg == "es" or kw.arg.endswith("_es")):
                    mark(kw.value)
    return marked


def py_texts(source: str):
    """(line, text, certain) of every string constant that is not a docstring."""
    tree = ast.parse(source)
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docs.add(id(first.value))
    certain = _py_certain(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            yield node.lineno, node.end_lineno or node.lineno, node.value, id(node) in certain


# --- TypeScript -----------------------------------------------------------------------------------------------------------

def ts_tokens(src: str, line: int = 1):
    """(kind, value, line) tokens: ``str`` (a string or a template literal part), ``id`` and ``p`` (punctuation)."""
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += src.count("\n", i, j)
            i = j
        elif c in "'\"":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            yield "str", _unescape(src[i + 1:j]), line
            i = j + 1
        elif c == "`":
            j, start, ln = i + 1, i + 1, line
            while j < n and src[j] != "`":
                if src[j] == "\\":
                    j += 2
                elif src.startswith("${", j):
                    yield "str", _unescape(src[start:j]), ln
                    ln += src.count("\n", start, j)
                    depth, k = 1, j + 2
                    while k < n and depth:
                        if src[k] == "{":
                            depth += 1
                        elif src[k] == "}":
                            depth -= 1
                        elif src[k] in "'\"`":
                            q = src[k]
                            k += 1
                            while k < n and src[k] != q:
                                k += 2 if src[k] == "\\" else 1
                        k += 1
                    yield from ts_tokens(src[j + 2:k - 1], ln)
                    ln += src.count("\n", j, k)
                    j = start = k
                else:
                    j += 1
            yield "str", _unescape(src[start:j]), ln
            line += src.count("\n", i, j + 1)
            i = j + 1
        elif c.isalpha() or c in "_$":
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            yield "id", src[i:j], line
            i = j
        else:
            yield "p", c, line
            i += 1


def _unescape(raw: str) -> str:
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            if nxt == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", raw[i + 2:i + 6]):
                out.append(chr(int(raw[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
            i += 2
        else:
            out.append(raw[i])
            i += 1
    return "".join(out)


def ts_texts(source: str):
    """(line, text, certain) of the strings of a TypeScript file; certain after ``es:`` / ``*_es:`` and in t() after its first argument."""
    stack: list[dict] = []       # open brackets: {"call_t": bool, "arg": int}
    es_depth = None              # bracket depth at which an es value started
    toks = list(ts_tokens(source))
    for idx, (kind, value, line) in enumerate(toks):
        nxt = toks[idx + 1] if idx + 1 < len(toks) else ("", "", 0)
        if kind == "p":
            if value in "([{":
                prev = toks[idx - 1] if idx else ("", "", 0)
                stack.append({"call_t": value == "(" and prev[0] == "id" and prev[1] in HELPERS, "arg": 0})
            elif value in ")]}":
                if stack:
                    stack.pop()
                if es_depth is not None and len(stack) < es_depth:
                    es_depth = None
            elif value == "," and stack:
                stack[-1]["arg"] += 1
                if es_depth is not None and len(stack) == es_depth:
                    es_depth = None
            elif value == ";" and es_depth is not None and len(stack) <= es_depth:
                es_depth = None
        elif kind == "id" and (value == "es" or value.endswith("_es")) and nxt[:2] == ("p", ":"):
            es_depth = len(stack)
        elif kind == "str":
            in_t = bool(stack) and stack[-1]["call_t"] and stack[-1]["arg"] >= 1
            yield line, value, in_t or es_depth is not None


JSX_TEXT = re.compile(r">([^<>{}=;]{3,}?)(?=<|\{)|\}([^<>{}=;]{3,}?)(?=<|\{)|\n[ \t]+([A-Za-zÀ-ÿ¿¡][^<>{}=;\n]{8,})(?=\n)", re.S)


def jsx_texts(source: str):
    for m in JSX_TEXT.finditer(source):
        seg = next(g for g in m.groups() if g)
        if re.search(r"['\"`()]", seg):
            continue    # code, not JSX text
        yield source.count("\n", 0, m.start(len(m.groups()) and [i for i, g in enumerate(m.groups(), 1) if g][0])) + 1, seg, False


# --- JSON -----------------------------------------------------------------------------------------------------------------

def json_texts(obj, only_es: bool, in_es: bool = False):
    """Every string of a JSON value; with ``only_es``, those under an ``es`` or ``*_es`` key."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from json_texts(v, only_es, in_es or k == "es" or k.endswith("_es"))
    elif isinstance(obj, list):
        for v in obj:
            yield from json_texts(v, only_es, in_es)
    elif isinstance(obj, str) and (in_es or not only_es):
        yield obj, in_es


def copied_pairs(obj):
    """The ``en`` text of every object with ``en`` and ``es`` strings that are equal, the ``en`` having three words or more."""
    if isinstance(obj, dict):
        en, es = obj.get("en"), obj.get("es")
        if isinstance(en, str) and isinstance(es, str) and en.strip() == es.strip() and len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", en)) >= 3:
            yield en
        for v in obj.values():
            yield from copied_pairs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from copied_pairs(v)


def load_copies(path: Path | None) -> tuple[dict[tuple[str, str], bool], list[str]]:
    """The allowed copies ``(path, text) -> used`` and the lines that carry no reason."""
    allow: dict[tuple[str, str], bool] = {}
    bad: list[str] = []
    if path and path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            body, _, reason = raw.partition("  # ")
            if not reason.strip() or "::" not in body:
                bad.append(raw.strip())
                continue
            where, text = (part.strip() for part in body.split("::", 1))
            allow[(where, text)] = False
    return allow, bad


def _line_of(lines: list[str], first: int, last: int, word: str) -> int:
    for no in range(first, min(last, len(lines)) + 1):
        if re.search(r"(?<![A-Za-zÀ-ÿ])" + re.escape(word) + r"(?![A-Za-zÀ-ÿ])", lines[no - 1]):
            return no
    return first


def scan_file(path: Path, rel: str, words: dict[str, str], documents: bool):
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    found = []
    if path.suffix == ".py":
        for first, last, text, certain in py_texts(src):
            for word, fix in check_text(text, certain, words):
                found.append((rel, _line_of(lines, first, last, word.split("_")[0]) if last > first else first, word, fix))
    elif path.suffix in (".ts", ".tsx"):
        for line, text, certain in ts_texts(src):
            for word, fix in check_text(text, certain, words):
                found.append((rel, _line_of(lines, line, line + text.count("\n") + 2, word), word, fix))
        if path.suffix == ".tsx":
            for line, text, certain in jsx_texts(src):
                for word, fix in check_text(text, certain, words):
                    found.append((rel, _line_of(lines, line, line + text.count("\n"), word), word, fix))
    elif path.suffix == ".json":
        for text, certain in json_texts(json.loads(src), only_es=documents):
            for word, fix in check_text(text, certain, words):
                found.append((rel, _line_of(lines, 1, len(lines), word), word, fix))
    return list(dict.fromkeys(found))


def collect(root: Path, documents: bool, explicit: list[str]) -> list[Path]:
    if explicit:
        return [root / p for p in explicit]
    if documents:
        return sorted((root / DOC_ROOT).rglob("*.json"))
    files: list[Path] = []
    for rel in CODE_ROOTS:
        base = root / rel
        files += [p for p in base.rglob("*") if p.suffix in (".py", ".json")]
    for p in (root / UI_ROOT).rglob("*"):
        if p.suffix in (".ts", ".tsx") and not re.search(r"\.(test|gen)\.tsx?$", p.name):
            files.append(p)
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", help="files to scan, relative to the root (default: the code, or the documents)")
    ap.add_argument("--root", type=Path, default=HERE.parent)
    ap.add_argument("--documents", action="store_true", help="read the es values of data/derived instead of the code")
    ap.add_argument("--words", type=Path, default=HERE / "check_spanish_words.txt")
    ap.add_argument("--allow", type=Path, default=None, help="default: scripts/check_spanish_allow.txt under the root")
    ap.add_argument("--copies", type=Path, default=None, help="default: scripts/check_spanish_copies.txt under the root")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")   # the fixes carry accents; a Windows console defaults to cp1252
        except (ValueError, OSError):
            pass
    root = args.root.resolve()
    words = load_words(args.words)
    args.allow = args.allow or root / "scripts" / "check_spanish_allow.txt"
    allow = load_allow(args.allow)
    findings = []
    copies, no_reason = load_copies(args.copies or root / "scripts" / "check_spanish_copies.txt") if args.documents else ({}, [])
    for line in no_reason:
        findings.append(("scripts/check_spanish_copies.txt", 0, "a copy entry needs a reason after '  # '", line))
    for path in collect(root, args.documents, args.paths):
        rel = path.relative_to(root).as_posix()
        if args.documents and path.suffix == ".json":
            doc_lines = path.read_text(encoding="utf-8").splitlines()
            for en in dict.fromkeys(copied_pairs(json.loads(path.read_text(encoding="utf-8")))):
                if (rel, en) in copies:
                    copies[(rel, en)] = True
                    continue
                first = en.splitlines()[0][:40]
                at = next((n for n, ln in enumerate(doc_lines, 1) if first in ln), 1)
                findings.append((rel, at, "es copies the English", f"translate: {en[:70]}"))
        for item in scan_file(path, rel, words, args.documents):
            key = (item[0], item[2].lower())
            if key in allow:
                allow[key] = True
            else:
                findings.append(item)
    for rel, line, word, fix in findings:
        print(f"{rel}:{line}: {word} -> {fix}")
    if not args.documents and not args.paths:
        for (where, word), used in allow.items():
            if not used:
                print(f"{args.allow.name}: unused allow entry: {where} :: {word}")
                findings.append((where, 0, word, ""))
    print(f"check_spanish: {len(findings)} finding{'s' if len(findings) != 1 else ''}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
