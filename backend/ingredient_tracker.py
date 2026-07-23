from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any


OUTSIDE = "outside"
INSIDE = "inside"
BETWEEN = "between"


@dataclass(frozen=True)
class TrackingSettings:
    inside_direction: str = "down"
    outer_line_ratio: float = 0.35
    inner_line_ratio: float = 0.65
    stable_zone_frames: int = 2
    max_center_distance_ratio: float = 0.25
    max_missed_frames: int = 3

    def __post_init__(self) -> None:
        if self.inside_direction not in {"up", "down", "left", "right"}:
            raise ValueError("inside_direction must be up, down, left or right")
        if not 0.0 <= self.outer_line_ratio < self.inner_line_ratio <= 1.0:
            raise ValueError("line ratios must satisfy 0 <= outer < inner <= 1")
        if self.stable_zone_frames < 1:
            raise ValueError("stable_zone_frames must be at least 1")
        if self.max_center_distance_ratio <= 0:
            raise ValueError("max_center_distance_ratio must be positive")
        if self.max_missed_frames < 0:
            raise ValueError("max_missed_frames cannot be negative")


@dataclass(frozen=True)
class TrackObservation:
    label: str
    coords: tuple[int, int, int, int]
    payload: Any = None


@dataclass(frozen=True)
class CrossingEvent:
    track_id: int
    label: str
    direction: str
    observation: TrackObservation


@dataclass
class _Track:
    track_id: int
    observation: TrackObservation
    stable_zone: str | None = None
    pending_zone: str | None = None
    pending_zone_frames: int = 0
    missed_frames: int = 0


def box_center(coords: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = coords
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


class IngredientCrossingTracker:
    """Associates labelled boxes and emits events after a full boundary crossing."""

    def __init__(self, settings: TrackingSettings) -> None:
        self.settings = settings
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)

    def update(
        self,
        observations: list[TrackObservation],
        frame_width: int,
        frame_height: int,
    ) -> list[CrossingEvent]:
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")

        matches, unmatched_tracks, unmatched_observations = self._associate(
            observations,
            frame_width,
            frame_height,
        )
        events: list[CrossingEvent] = []

        for track_id, observation_index in matches:
            track = self._tracks[track_id]
            track.observation = observations[observation_index]
            track.missed_frames = 0
            event = self._update_zone(track, frame_width, frame_height)
            if event is not None:
                events.append(event)

        for track_id in unmatched_tracks:
            self._tracks[track_id].missed_frames += 1

        expired = [
            track_id
            for track_id, track in self._tracks.items()
            if track.missed_frames > self.settings.max_missed_frames
        ]
        for track_id in expired:
            del self._tracks[track_id]

        for observation_index in unmatched_observations:
            track = _Track(self._next_track_id, observations[observation_index])
            self._next_track_id += 1
            self._tracks[track.track_id] = track
            self._update_zone(track, frame_width, frame_height)

        return events

    def _associate(
        self,
        observations: list[TrackObservation],
        frame_width: int,
        frame_height: int,
    ) -> tuple[list[tuple[int, int]], set[int], set[int]]:
        diagonal = hypot(frame_width, frame_height)
        possible_matches: list[tuple[float, int, int]] = []

        for track_id, track in self._tracks.items():
            previous_center = box_center(track.observation.coords)
            for observation_index, observation in enumerate(observations):
                if observation.label != track.observation.label:
                    continue
                current_center = box_center(observation.coords)
                distance_ratio = hypot(
                    current_center[0] - previous_center[0],
                    current_center[1] - previous_center[1],
                ) / diagonal
                if distance_ratio <= self.settings.max_center_distance_ratio:
                    possible_matches.append((distance_ratio, track_id, observation_index))

        matches: list[tuple[int, int]] = []
        matched_tracks: set[int] = set()
        matched_observations: set[int] = set()
        for _, track_id, observation_index in sorted(possible_matches):
            if track_id in matched_tracks or observation_index in matched_observations:
                continue
            matches.append((track_id, observation_index))
            matched_tracks.add(track_id)
            matched_observations.add(observation_index)

        return (
            matches,
            set(self._tracks) - matched_tracks,
            set(range(len(observations))) - matched_observations,
        )

    def _update_zone(
        self,
        track: _Track,
        frame_width: int,
        frame_height: int,
    ) -> CrossingEvent | None:
        zone = self._zone(track.observation.coords, frame_width, frame_height)
        if zone == BETWEEN:
            track.pending_zone = None
            track.pending_zone_frames = 0
            return None

        if track.pending_zone == zone:
            track.pending_zone_frames += 1
        else:
            track.pending_zone = zone
            track.pending_zone_frames = 1

        if track.pending_zone_frames < self.settings.stable_zone_frames:
            return None
        if track.stable_zone == zone:
            return None

        previous_stable_zone = track.stable_zone
        track.stable_zone = zone
        if previous_stable_zone == OUTSIDE and zone == INSIDE:
            direction = "in"
        elif previous_stable_zone == INSIDE and zone == OUTSIDE:
            direction = "out"
        else:
            return None

        return CrossingEvent(
            track_id=track.track_id,
            label=track.observation.label,
            direction=direction,
            observation=track.observation,
        )

    def _zone(
        self,
        coords: tuple[int, int, int, int],
        frame_width: int,
        frame_height: int,
    ) -> str:
        center_x, center_y = box_center(coords)
        direction = self.settings.inside_direction
        if direction == "down":
            progress = center_y / frame_height
        elif direction == "up":
            progress = 1.0 - center_y / frame_height
        elif direction == "right":
            progress = center_x / frame_width
        else:
            progress = 1.0 - center_x / frame_width

        if progress <= self.settings.outer_line_ratio:
            return OUTSIDE
        if progress >= self.settings.inner_line_ratio:
            return INSIDE
        return BETWEEN
