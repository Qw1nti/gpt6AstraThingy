"""Short-lived box association and bounded motion extrapolation, without identity recognition."""
from dataclasses import dataclass
import math

from .core import Box, overlap

PREDICTION_HORIZON = .12


@dataclass
class Track:
    box: Box
    observed: float
    received: float
    patch: object = None
    vx: float = 0
    vy: float = 0
    hits: int = 1


def center(box):
    return ((box.left+box.right)/2, (box.top+box.bottom)/2)


def project(track, at, width, height):
    dt = min(PREDICTION_HORIZON, max(0, at-track.observed))
    max_shift = min(128, max(track.box.right-track.box.left, track.box.bottom-track.box.top))
    dx = max(-max_shift, min(max_shift, track.vx*dt))
    dy = max(-max_shift, min(max_shift, track.vy*dt))
    box = track.box
    return Box(max(0, round(box.left+dx)), max(0, round(box.top+dy)),
               min(width, round(box.right+dx)), min(height, round(box.bottom+dy)), box.score, box.category)


class MotionTracker:
    def __init__(self):
        self.tracks = []
        self.last_observation = None

    def update(self, boxes, patches, observed, received, size, ttl):
        if self.last_observation is not None and observed <= self.last_observation:
            return
        self.last_observation = observed
        self.tracks = [track for track in self.tracks if received-track.received <= ttl]
        candidates = []
        for old_index, track in enumerate(self.tracks):
            predicted = project(track, observed, *size)
            pc = center(predicted)
            for new_index, box in enumerate(boxes):
                if box.category != track.box.category:
                    continue
                nc = center(box)
                distance = math.hypot(nc[0]-pc[0], nc[1]-pc[1])
                edge = max(box.right-box.left, box.bottom-box.top, 1)
                old_edge = max(track.box.right-track.box.left, track.box.bottom-track.box.top, 1)
                dt = observed-track.observed
                gate = min(128, max(40, edge*1.2, dt*500))
                if .4 <= edge/old_edge <= 2.5 and dt <= .75 and distance <= gate:
                    candidates.append((distance/edge-2*overlap(predicted, box), old_index, new_index))
        used_old, used_new = set(), set()
        for _, old_index, new_index in sorted(candidates):
            if old_index in used_old or new_index in used_new:
                continue
            track, box = self.tracks[old_index], boxes[new_index]
            old_center, new_center = center(track.box), center(box)
            dt = max(.001, observed-track.observed)
            vx, vy = ((new_center[i]-old_center[i])/dt for i in (0, 1))
            alpha = 1 if track.hits == 1 else .65
            track.vx = max(-2000, min(2000, alpha*vx+(1-alpha)*track.vx))
            track.vy = max(-2000, min(2000, alpha*vy+(1-alpha)*track.vy))
            track.box, track.observed, track.received = box, observed, received
            track.patch = patches[new_index] if new_index < len(patches) else None
            track.hits += 1
            used_old.add(old_index)
            used_new.add(new_index)
        # If every detection jumps to a new location, discard old scene positions.
        if boxes and not used_old:
            self.tracks.clear()
        for index, box in enumerate(boxes):
            if index not in used_new:
                self.tracks.append(Track(box, observed, received,
                                         patches[index] if index < len(patches) else None))

    def render(self, at, size, ttl):
        self.tracks = [track for track in self.tracks if at-track.received <= ttl]
        boxes, patches = [], []
        for track in self.tracks:
            box = project(track, at, *size)
            if box.right > box.left and box.bottom > box.top:
                boxes.append(box)
                patches.append(track.patch)
        return boxes, patches
