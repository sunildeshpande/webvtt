#!/usr/bin/env python3
"""
Minimal WebVTT sentiment analyzer.

Reads cues from a .vtt file, scores each cue using a small
positive/negative lexicon, and prints cue-level plus aggregate results.
"""

import argparse
import pathlib
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "happy", "joy", "love",
    "fantastic", "positive", "success", "enjoy", "wonderful", "smile",
    "delight", "peace", "win", "friendly", "brilliant", "calm", "progress",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "sad", "angry", "hate", "horrible",
    "negative", "fail", "failure", "worse", "worst", "pain", "fear",
    "problem", "loss", "cry", "danger", "frustrated", "stress",
}

TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})$")


@dataclass
class Cue:
    index: int
    cue_id: Optional[str]
    start: float
    end: float
    text: str


@dataclass
class SentimentResult:
    score: int = 0
    positives: int = 0
    negatives: int = 0
    total_words: int = 0

    def update(self, other: "SentimentResult") -> None:
        self.score += other.score
        self.positives += other.positives
        self.negatives += other.negatives
        self.total_words += other.total_words


def parse_timestamp(value: str) -> float:
    match = TIMESTAMP_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4))
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def parse_timing_line(line: str) -> (float, float):
    if "-->" not in line:
        raise ValueError("Missing cue timing separator '-->'")
    start_chunk, rest = line.split("-->", 1)
    start = parse_timestamp(start_chunk.strip())
    rest = rest.strip()
    # Settings may trail end timestamp; only take the timestamp token.
    end_token = rest.split()[0]
    end = parse_timestamp(end_token)
    return start, end


def iter_blocks(lines: Iterable[str]) -> Iterable[List[str]]:
    block: List[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.strip() == "":
            if block:
                yield block
                block = []
        else:
            block.append(line)
    if block:
        yield block


def parse_vtt(path: pathlib.Path) -> List[Cue]:
    with path.open(encoding="utf-8-sig") as handle:
        lines = handle.readlines()

    cues: List[Cue] = []
    iterator = iter_blocks(lines)
    first_block_skipped = False
    for block in iterator:
        if not first_block_skipped:
            first_block_skipped = True
            if block and block[0].lstrip("\ufeff").upper().startswith("WEBVTT"):
                continue
            # If header missing, proceed to treat this block as a cue.
        if block[0].startswith("NOTE"):
            continue

        cue_id = None
        timing_index = 0
        if "-->" not in block[0]:
            cue_id = block[0]
            timing_index = 1
        if timing_index >= len(block):
            continue
        try:
            start, end = parse_timing_line(block[timing_index])
        except ValueError:
            continue
        text_lines = block[timing_index + 1 :]
        text = "\n".join(text_lines).strip()
        cues.append(Cue(len(cues) + 1, cue_id, start, end, text))
    return cues


def analyze_text(text: str) -> SentimentResult:
    result = SentimentResult()
    for word in re.findall(r"[A-Za-z]+", text or ""):
        result.total_words += 1
        token = word.lower()
        if token in POSITIVE_WORDS:
            result.positives += 1
            result.score += 1
        elif token in NEGATIVE_WORDS:
            result.negatives += 1
            result.score -= 1
    return result


def analyze_file(path: pathlib.Path) -> None:
    cues = parse_vtt(path)
    aggregate = SentimentResult()
    if not cues:
        print(f"No cues parsed from `{path}`.")
        return
    for cue in cues:
        sentiment = analyze_text(cue.text)
        aggregate.update(sentiment)
        text_preview = cue.text.replace("\n", " ")
        print(f"Cue {cue.index}: \"{text_preview}\"")
        print(
            f"  Sentiment score: {sentiment.score} "
            f"(positive {sentiment.positives} / negative {sentiment.negatives})"
        )
    avg = aggregate.score / len(cues)
    print(f"\nProcessed {len(cues)} cues from `{path}`")
    print(f"Aggregate sentiment score: {aggregate.score}")
    print(f"Average sentiment per cue: {avg:.2f}")
    print(
        f"Positive matches: {aggregate.positives} | "
        f"Negative matches: {aggregate.negatives}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze sentiment of cues within a WebVTT subtitle file."
    )
    parser.add_argument(
        "vtt_file",
        type=pathlib.Path,
        help="Path to the .vtt file to analyze",
    )
    args = parser.parse_args()
    analyze_file(args.vtt_file)


if __name__ == "__main__":
    main()
