"""Media rules: MediaRule, AudioTranscriptRule."""

from __future__ import annotations
import re

from a11y_context import ParseContext, TagAttrs, AudioEntry
from a11y_rules.base import A11yRule


class MediaRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "video":
            ctx.media.video_depth += 1
            if ctx.media.video_depth == 1:
                ctx.media.current_video = {"line": line, "has_captions": False}
            return

        if tag == "track" and ctx.media.video_depth > 0 and ctx.media.current_video:
            if attrs.get_lower("kind") == "captions":
                ctx.media.current_video["has_captions"] = True
            return

        if tag == "audio":
            # find offset
            occurrence = len([entry for entry in ctx.media.audio_entries if entry.line == line])
            idx = 0
            offset = 0
            for match in re.finditer(r"<audio\b", ctx.source, re.IGNORECASE):
                match_line = ctx.source[: match.start()].count("\n") + 1
                if match_line == line:
                    if idx == occurrence:
                        offset = match.start()
                        break
                    idx += 1

            ctx.media.audio_entries.append(AudioEntry(line=line, offset=offset))

            if attrs.has("autoplay"):
                ctx.add_violation(
                    id="no-autoplay",
                    severity="serious",
                    line=line,
                    message="Media with autoplay — can disorient screen reader users and violate WCAG 1.4.2",
                    fix="Remove autoplay, or add controls and a mechanism to pause/stop the media",
                    wcag="1.4.2 Audio Control",
                )

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "video":
            return
        if ctx.media.video_depth == 1 and ctx.media.current_video and not ctx.media.current_video["has_captions"]:
            ctx.add_violation(
                id="video-captions",
                severity="serious",
                line=ctx.media.current_video["line"],
                message='<video> is missing a <track kind="captions"> element',
                fix='Add <track kind="captions" src="captions.vtt" srclang="en" label="English"> inside the video',
                wcag="1.2.2 Captions (Prerecorded)",
            )
        if ctx.media.current_video and ctx.media.video_depth == 1:
            ctx.media.current_video = None
        ctx.media.video_depth = max(0, ctx.media.video_depth - 1)


class AudioTranscriptRule(A11yRule):
    def finalize(self, ctx: ParseContext) -> None:
        if not ctx.source or not ctx.media.audio_entries:
            return
        for entry in ctx.media.audio_entries:
            window = ctx.source[entry.offset : entry.offset + 500].lower()
            if "transcript" not in window:
                ctx.add_violation(
                    id="audio-transcript",
                    severity="serious",
                    line=entry.line,
                    message="<audio> element has no nearby transcript link or text (heuristic)",
                    fix='Provide a transcript link or text adjacent to the audio, e.g. <a href="transcript.html">Transcript</a>',
                    wcag="1.2.1 Audio-only and Video-only (Prerecorded)",
                )
