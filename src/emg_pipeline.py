"""Protocol v1.0 raw-range partitioning and causal EMG feature extraction.

No decoder, controller selection, or scientific outcome evaluation occurs here.
Indices are zero-based; all raw ranges and windows are half-open. Offline
annotations define experimental partitions, never online controller inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import io
import json
import zipfile

import numpy as np
from scipy.io import loadmat
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class Bout:
    label: int
    repetition: int
    start: int
    end: int


@dataclass(frozen=True)
class Cell:
    index: int
    start: int
    end: int
    role: str
    bout: Bout


@dataclass(frozen=True)
class Block:
    index: int
    start: int
    end: int
    role: str
    cell_indices: tuple[int, ...]


@dataclass(frozen=True)
class Recording:
    subject: int
    fs: int
    emg: np.ndarray
    truth: np.ndarray
    repetitions: np.ndarray
    stimulus: np.ndarray
    source_member: str = "synthetic"


@dataclass(frozen=True)
class Frames:
    subject: int
    role: str
    window_samples: int
    hop_samples: int
    fs: int
    starts: np.ndarray
    ends: np.ndarray
    block_ids: np.ndarray
    labels: np.ndarray
    features: np.ndarray

    @property
    def times_seconds(self):
        return self.ends / self.fs


def samples(ms: int, fs: int) -> int:
    value = ms * fs / 1000
    if ms <= 0 or fs <= 0 or int(value) != value:
        raise ValueError("Duration must be positive and exactly representable")
    return int(value)


def load_protocol(root: Path) -> dict:
    """Check every frozen-file hash before using the specification."""
    root = Path(root)
    freeze = json.loads((root / "docs/step4_protocol/FREEZE_RECORD_v1.0.json").read_text())
    for name, expected in freeze["frozen_file_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen specification changed: {name}")
    return json.loads((root / "config/protocol_v1.0.json").read_text())


def load_recording(root: Path, subject: int, protocol: dict) -> Recording:
    """Load only primary E2, verifying the exact archived bytes and known aliases."""
    inventory = json.loads((Path(root) / protocol["source_inventory"]).read_text())
    rows = [r for r in inventory if r["subject"] == subject]
    if len(rows) != 1:
        raise ValueError("Participant absent or duplicated in source inventory")
    row = rows[0]
    archive = (Path(root) / row["local_path"]).read_bytes()
    if hashlib.sha256(archive).hexdigest() != row["sha256"]:
        raise ValueError("Source archive SHA256 mismatch")
    member = f"s{subject}/S{subject}_E2_A1.mat"
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        d = loadmat(io.BytesIO(z.read(member)), variable_names=[
            "emg", "restimulus", "rerepetition", "stimulus",
            "subject", "exercise", "frequency",
        ])
    if (int(d["subject"].item()) != (11 if subject == 2 else subject)
            or int(d["exercise"].item()) != protocol["mat_exercise_scalar"]
            or int(d["frequency"].item()) != protocol["sampling_rate_hz"]):
        raise ValueError("Unexpected source identity, task, or frequency")
    emg = np.asarray(d["emg"])
    y, rep, prompt = (np.asarray(d[k]).ravel().astype(np.int64)
                      for k in ("restimulus", "rerepetition", "stimulus"))
    if emg.shape != (len(y), len(protocol["channels"])):
        raise ValueError("Unexpected EMG dimensions")
    if len(rep) != len(y) or len(prompt) != len(y):
        raise ValueError("Signal/annotation lengths differ")
    if not np.isfinite(emg).all() or set(np.unique(y)) != set(protocol["class_labels"]):
        raise ValueError("Invalid signal values or label inventory")
    for a in (emg, y, rep, prompt):
        a.setflags(write=False)
    return Recording(subject, protocol["sampling_rate_hz"], emg, y, rep, prompt, member)


def find_bouts(truth: np.ndarray, repetitions: np.ndarray) -> list[Bout]:
    y, r = np.asarray(truth), np.asarray(repetitions)
    if y.ndim != 1 or r.shape != y.shape or not len(y):
        raise ValueError("Equal nonempty annotation vectors required")
    boundaries = np.flatnonzero(np.r_[True, (y[1:] != y[:-1]) | (r[1:] != r[:-1])])
    ends = np.r_[boundaries[1:], len(y)]
    bouts = [Bout(int(y[a]), int(r[a]), int(a), int(b))
             for a, b in zip(boundaries, ends) if y[a] != 0]
    if not bouts or any(b.label < 1 or not 1 <= b.repetition <= 6 for b in bouts):
        raise ValueError("Invalid or absent active bouts")
    return bouts


def repetition_roles(subject: int, protocol: dict) -> dict[int, str]:
    roles = {r: "train" for r in protocol["decoder_train_repetitions"]}
    if subject in protocol["development_subjects"]:
        extra = {r: "selection" for r in protocol["development_selection_repetitions"]}
    elif subject in protocol["confirmatory_subjects"]:
        extra = {r: "evaluation" for r in protocol["confirmatory_evaluation_repetitions"]}
        extra.update({r: "unused" for r in protocol["confirmatory_unused_repetitions"]})
    else:
        raise ValueError("Unknown participant")
    if set(roles) & set(extra) or set(roles) | set(extra) != set(range(1, 7)):
        raise ValueError("Invalid or overlapping repetition roles")
    return roles | extra


def partition(n_samples: int, bouts: list[Bout], roles: dict[int, str]):
    if (n_samples < 1 or not bouts
            or any(b.start < 0 or b.end <= b.start or b.end > n_samples for b in bouts)):
        raise ValueError("Invalid bout extent")
    if any(a.end > b.start for a, b in zip(bouts, bouts[1:])):
        raise ValueError("Bouts overlap or are unsorted")
    edges = [0] + [(a.end + b.start) // 2 for a, b in zip(bouts, bouts[1:])] + [n_samples]
    cells = [Cell(i, edges[i], edges[i + 1], roles[b.repetition], b)
             for i, b in enumerate(bouts)]
    blocks: list[Block] = []
    for c in cells:
        if blocks and blocks[-1].role == c.role and blocks[-1].end == c.start:
            previous = blocks.pop()
            blocks.append(Block(previous.index, previous.start, c.end, c.role,
                                previous.cell_indices + (c.index,)))
        else:
            blocks.append(Block(len(blocks), c.start, c.end, c.role, (c.index,)))
    validate_partition(n_samples, cells, blocks)
    return cells, blocks


def validate_partition(n_samples: int, cells: list[Cell], blocks: list[Block]):
    for intervals in (cells, blocks):
        if not intervals or intervals[0].start != 0 or intervals[-1].end != n_samples:
            raise ValueError("Partition does not cover entire recording")
        if any(x.end <= x.start for x in intervals):
            raise ValueError("Empty partition interval")
        if any(a.end != b.start for a, b in zip(intervals, intervals[1:])):
            raise ValueError("Partition has a gap or overlap")
    used = []
    for b in blocks:
        owned = [cells[i] for i in b.cell_indices]
        if (owned[0].start != b.start or owned[-1].end != b.end
                or any(c.role != b.role for c in owned)):
            raise ValueError("Block ownership mismatch")
        used.extend(b.cell_indices)
    if used != list(range(len(cells))):
        raise ValueError("Cell duplicated or omitted")
    if any(a.role == b.role for a, b in zip(blocks, blocks[1:])):
        raise ValueError("Touching same-role cells must be merged")


def endpoints(block: Block, length: int, hop: int) -> np.ndarray:
    if length < 2 or hop < 1:
        raise ValueError("Window length>=2 and positive hop required")
    first = ((block.start + length + hop - 1) // hop) * hop
    return np.arange(first, block.end + 1, hop, dtype=np.int64)


def feature_matrix(emg: np.ndarray, ends: np.ndarray, length: int,
                   chunk_size: int = 1024) -> np.ndarray:
    """Return channel-major [MAV,RMS,meanWL], using precisely [e-L,e)."""
    x, ends = np.asarray(emg), np.asarray(ends)
    if x.ndim != 2 or length < 2 or chunk_size < 1:
        raise ValueError("Invalid EMG or extraction settings")
    if ends.ndim != 1 or not np.issubdtype(ends.dtype, np.integer):
        raise ValueError("Integer window endpoints required")
    if len(ends) and (np.min(ends) < length or np.max(ends) > len(x)):
        raise ValueError("Window outside recording")
    result = np.empty((len(ends), 3 * x.shape[1]), dtype=np.float64)
    offsets = np.arange(-length, 0)
    for start in range(0, len(ends), chunk_size):
        ee = ends[start:start + chunk_size]
        # Cast before squaring/differencing: input may be signed integer EMG.
        windows = x[ee[:, None] + offsets[None, :]].astype(np.float64)
        features = np.stack((np.mean(np.abs(windows), axis=1),
                             np.sqrt(np.mean(windows * windows, axis=1)),
                             np.mean(np.abs(np.diff(windows, axis=1)), axis=1)), axis=2)
        result[start:start + len(ee)] = features.reshape(len(ee), -1)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite features")
    return result


def make_frames(recording: Recording, blocks: list[Block], role: str,
                window_ms: int = 150, hop_ms: int = 25) -> Frames:
    if (not blocks or blocks[0].start != 0 or blocks[-1].end != len(recording.emg)
            or len({b.index for b in blocks}) != len(blocks)
            or any(b.end <= b.start for b in blocks)
            or any(a.end != b.start for a, b in zip(blocks, blocks[1:]))):
        raise ValueError("Complete, nonoverlapping raw block partition required")
    length, hop = samples(window_ms, recording.fs), samples(hop_ms, recording.fs)
    selected = [b for b in blocks if b.role == role]
    ends = [endpoints(b, length, hop) for b in selected]
    ee = np.concatenate(ends) if ends else np.empty(0, dtype=np.int64)
    ids = np.concatenate([np.full(len(e), b.index, dtype=np.int64)
                          for b, e in zip(selected, ends)]) if ends else np.empty(0, dtype=np.int64)
    for b, e in zip(selected, ends):
        if np.any(e - length < b.start) or np.any(e > b.end):
            raise AssertionError("Cross-block window")
    return Frames(recording.subject, role, length, hop, recording.fs,
                  ee - length, ee, ids, recording.truth[ee - 1].copy(),
                  feature_matrix(recording.emg, ee, length))


@dataclass(frozen=True)
class TrainingScaler:
    subject: int
    feature_count: int
    window_samples: int
    hop_samples: int
    fs: int
    scaler: StandardScaler

    def transform(self, frames: Frames) -> np.ndarray:
        if (frames.subject != self.subject or frames.features.shape[1] != self.feature_count
                or frames.window_samples != self.window_samples
                or frames.hop_samples != self.hop_samples or frames.fs != self.fs):
            raise ValueError("Scaler belongs to another person or window/feature schema")
        return self.scaler.transform(frames.features)


def fit_training_scaler(frames: Frames) -> TrainingScaler:
    if frames.role != "train" or not len(frames.features):
        raise ValueError("Fit normalization on nonempty training frames only")
    fitted = StandardScaler().fit(frames.features)
    return TrainingScaler(frames.subject, frames.features.shape[1], frames.window_samples,
                          frames.hop_samples, frames.fs, fitted)


def event_inventory(cells: list[Cell], blocks: list[Block], fs: int,
                    protocol: dict) -> list[dict]:
    """Eligibility uses annotation/range information, never a prediction."""
    e = protocol["eligibility"]
    min_active = samples(e["active_duration_min_ms"], fs)
    min_pre = samples(e["pre_onset_rest_min_ms"], fs)
    min_post = samples(e["post_offset_rest_min_ms"], fs)
    warmup = samples(protocol["common_warmup_exclusion_ms"], fs)
    by_cell = {i: b for b in blocks for i in b.cell_indices}
    result = []
    for c in cells:
        b, bout = by_cell[c.index], c.bout
        previous_end = cells[c.index - 1].bout.end if c.index else 0
        next_start = cells[c.index + 1].bout.start if c.index + 1 < len(cells) else cells[-1].end
        pre = bout.start - max(previous_end, b.start)
        post = min(next_start, b.end) - bout.end
        reasons = []
        if bout.end - bout.start < min_active:
            reasons.append("active_duration_under_1000ms")
        if pre < min_pre:
            reasons.append("preceding_rest_under_200ms_in_block")
        if post < min_post:
            reasons.append("following_rest_under_500ms_in_block")
        if bout.start < b.start + warmup:
            reasons.append("onset_before_common_warmup_end")
        result.append({"cell": c.index, "block": b.index, "role": c.role,
                       "label": bout.label, "repetition": bout.repetition,
                       "onset_sample": bout.start, "offset_sample": bout.end,
                       "preceding_rest_samples": pre, "following_rest_samples": post,
                       "eligible": not reasons, "exclusion_reasons": reasons})
    return result


def hold_outputs(block: Block, ends: np.ndarray, predictions: np.ndarray) -> np.ndarray:
    """Expand output state at each raw sample; begin each real block at rest."""
    ends, predictions = np.asarray(ends), np.asarray(predictions)
    if ends.shape != predictions.shape or ends.ndim != 1:
        raise ValueError("Equal endpoint/prediction vectors required")
    if not np.issubdtype(ends.dtype, np.integer):
        raise ValueError("Output timestamps must be integer sample indices")
    if len(ends) and (ends[0] < block.start or ends[-1] > block.end
                      or np.any(np.diff(ends) <= 0)):
        raise ValueError("Endpoints outside block or non-increasing")
    out = np.zeros(block.end - block.start, dtype=np.int64)
    for end, stop, value in zip(ends, np.r_[ends[1:], block.end], predictions):
        out[int(end) - block.start:int(stop) - block.start] = value
    return out


def occupancy(truth: np.ndarray, held: np.ndarray, block: Block, fs: int,
              warmup_ms: int = 250) -> dict:
    """Time-weighted scaffolding; scientific outcome summaries belong to Step7+."""
    y = np.asarray(truth)[block.start:block.end]
    if np.asarray(held).shape != y.shape:
        raise ValueError("Held output must correspond exactly to one block")
    cut = min(len(y), samples(warmup_ms, fs))
    y, held = y[cut:], np.asarray(held)[cut:]
    return {"scored_samples": len(y), "warmup_excluded_samples": cut,
            "rest_samples": int(np.sum(y == 0)),
            "nonrest_output_during_rest_samples": int(np.sum((y == 0) & (held != 0)))}


def confirm_stable(ends: np.ndarray, predictions: np.ndarray, target: int,
                   reference: int, search_end: int, stable_samples: int,
                   hop_samples: int) -> int | None:
    """Return confirmation endpoint, never retroactively the start of its run."""
    ends, predictions = np.asarray(ends), np.asarray(predictions)
    if ends.shape != predictions.shape or stable_samples <= 0 or hop_samples <= 0:
        raise ValueError("Invalid stable-confirmation input")
    if len(ends) > 1 and np.any(np.diff(ends) != hop_samples):
        raise ValueError("Use one continuous block, not concatenated gaps")
    run_start = None
    for t, value in zip(ends, predictions):
        if t < reference:
            continue
        if t >= search_end:
            break
        if value != target:
            run_start = None
        elif run_start is None:
            run_start = t
        if run_start is not None and t - run_start >= stable_samples:
            return int(t)
    return None
