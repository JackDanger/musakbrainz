#!/usr/bin/env python3
"""
A merged script that:
1) Recursively scans a local directory to find all audio files (including 'Bonus Tracks' or subfolders).
2) Extracts metadata for each file (title, tracknumber, etc.) via mutagen.
3) Guesses the artist/album from the top-level directory name.
4) Looks up matching release data on MusicBrainz (musicbrainzngs).
5) Prints a side-by-side diff (left = local, right = MB),
   but if a line is identical in both, it shows it once in the center.

Usage:
  python complete_script.py "/path/to/A Plus D - Best of Bootie Mashup 2024"
"""

import os
import sys
import argparse
import re

import musicbrainzngs
from mutagen import File as MutagenFile

# Configure MusicBrainz
musicbrainzngs.set_useragent(
    "MusicBrainzSideBySideDiff",
    "0.1",
    "https://example.org/my-musicbrainz-app"
)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Recursively gather local tracks, then produce a side-by-side diff vs. MusicBrainz."
    )
    parser.add_argument(
        "root_directory",
        help="Root directory of the album (including subfolders)."
    )
    return parser.parse_args()


def guess_artist_and_album_from_directory(dir_name):
    """
    Naive approach: parse "Artist - Album" from directory name.
    If that fails, we treat the entire name as "album" and artist=None.
    Adjust as needed for your folder naming patterns.
    """
    pattern = r"^(.*?)\s*-\s*(.*)$"
    match = re.match(pattern, dir_name)
    if match:
        artist, album = match.groups()
        return artist.strip(), album.strip()
    return None, dir_name.strip()


# Expand to your typical set of audio file extensions
VALID_AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg"}


def find_audio_files_recursively(root_directory):
    """
    Walk 'root_directory' (and subdirs) to find valid audio files.
    Yields full file paths to each found audio file.
    """
    for dirpath, dirnames, filenames in os.walk(root_directory):
        # Optionally skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for fname in sorted(filenames):
            if fname.startswith('.'):
                continue
            full_path = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname.lower())[1]
            if ext in VALID_AUDIO_EXTENSIONS:
                yield full_path


def extract_tags_from_file(file_path):
    """
    Reads audio metadata via mutagen.
    Returns a dict with 'title', 'artist', 'tracknumber', etc.
    """
    audio_data = {
        "title": None,
        "artist": None,
        "tracknumber": None,
    }
    audio = MutagenFile(file_path)
    if not audio or not audio.tags:
        return audio_data

    tags = dict(audio.tags)

    # Title
    for key in ['TIT2', 'TITLE', '\xa9nam']:
        if key in tags:
            audio_data['title'] = str(tags[key])
            break

    # Artist
    for key in ['TPE1', 'ARTIST', '\xa9ART']:
        if key in tags:
            audio_data['artist'] = str(tags[key])
            break

    # Track number
    for key in ['TRCK', 'TRACKNUMBER']:
        if key in tags:
            raw = str(tags[key])  # e.g. "7/12"
            audio_data['tracknumber'] = raw.split('/')[0]
            break

    return audio_data


def gather_all_local_tracks(root_directory):
    """
    Recursively scans the root directory for valid audio files,
    returns a list of dicts with subdir, filename, metadata, etc.
    """
    root_directory = os.path.abspath(root_directory)
    all_tracks = []

    for audio_path in find_audio_files_recursively(root_directory):
        rel_path = os.path.relpath(audio_path, root_directory)
        subdir = os.path.dirname(rel_path)  # e.g. "Bonus Tracks" or "."
        if subdir == ".":
            subdir = ""  # no subdirectory

        metadata = extract_tags_from_file(audio_path)

        # Fallback if no tag-based title
        if not metadata['title']:
            metadata['title'] = os.path.splitext(os.path.basename(audio_path))[0]

        track_info = {
            "full_path": audio_path,
            "subdir": subdir,
            "filename": os.path.basename(audio_path),
            "title": metadata["title"],
            "artist": metadata["artist"],
            "tracknumber": metadata["tracknumber"],
        }
        all_tracks.append(track_info)

    return all_tracks


def find_best_release_match(artist_name, album_name):
    """
    Use MusicBrainz search to find a release that matches artist & album name.
    Returns the full release data (dictionary) if found, else None.
    """
    if not artist_name:
        result = musicbrainzngs.search_releases(release=album_name, limit=5)
    else:
        result = musicbrainzngs.search_releases(
            artist=artist_name,
            release=album_name,
            limit=5
        )

    releases = result.get('release-list', [])
    if not releases:
        return None

    # Take the first result for simplicity. Real code might do better.
    best_release = releases[0]
    release_id = best_release['id']
    try:
        full_release = musicbrainzngs.get_release_by_id(
            release_id,
            includes=["artist-credits", "recordings", "url-rels",
                      "labels", "release-groups"]
        )
        return full_release["release"]
    except musicbrainzngs.WebServiceError:
        return None


def side_by_side_format(
        lines_left,
        lines_right,
        left_width=60,
        unify_if_identical=True
    ):
    """
    Produce a list of strings showing side-by-side comparison.

    If `unify_if_identical` is True and a line is identical (and non-empty)
    on both sides, we display it once centered. Otherwise, we do left|right.

    Each non-unified line: left text padded to `left_width`, a separator,
    and the right text.
    """
    output = []
    max_len = max(len(lines_left), len(lines_right))
    total_width = left_width * 2 + 3  # 3 = space + '|' + space

    for i in range(max_len):
        left_line = lines_left[i] if i < len(lines_left) else ""
        right_line = lines_right[i] if i < len(lines_right) else ""

        if (unify_if_identical
                and left_line.strip()
                and left_line == right_line):
            # Show the identical line once, centered
            merged_line = f"          == {left_line}"
            output.append(merged_line)
        else:
            # Normal side-by-side
            output.append(f"{left_line:<{left_width}} | {right_line}")

    return output


def generate_side_by_side_diff(local_data, mb_data):
    """
    local_data is a dict:
       {
         "artist": ...,
         "album": ...,
         "tracks": [ { "filename":..., "title":..., etc. }, ... ]
       }

    mb_data is the MusicBrainz release dictionary.

    Returns a single string with a side-by-side diff:
      LEFT  = local data
      RIGHT = MusicBrainz data

    Identical lines appear once in the middle.
    """

    # --- Release-level lines (Left vs Right) ---
    local_artist = local_data["artist"] or "Unknown Local Artist"
    local_album = local_data["album"] or "Unknown Local Album"
    local_release_lines = [
        f"Artist: {local_artist}",
        f"Album:  {local_album}",
        "(subdir logic not shown at release-level)"
    ]

    # Build MB release lines
    mb_release_lines = []
    mb_artists = []
    for credit in mb_data.get('artist-credit', []):
        if isinstance(credit, dict) and "artist" in credit:
            mb_artists.append(credit["artist"]["name"])
        elif isinstance(credit, str):
            mb_artists.append(credit)

    mb_artist_joined = " & ".join(mb_artists) if mb_artists else "Unknown MB Artist"
    mb_release_lines.append(f"Artist: {mb_artist_joined}")

    mb_album = mb_data.get("title") or "Unknown MB Album"
    mb_release_lines.append(f"Album:  {mb_album}")

    release_id = mb_data.get('id')
    if release_id:
        mb_release_lines.append(
            f"MB Release URI: https://musicbrainz.org/release/{release_id}"
        )

    # Possibly show MB "url-rels"
    for urlrel in mb_data.get("url-relation-list", []):
        rel_type = urlrel.get('type')
        target = urlrel.get('target')
        mb_release_lines.append(f" - {rel_type}: {target}")

    release_info_diff = side_by_side_format(
        local_release_lines,
        mb_release_lines,
        left_width=60,
        unify_if_identical=True
    )

    # --- Track-level lines ---
    # Flatten MB's tracklists
    mb_tracks = []
    for medium in mb_data.get('medium-list', []):
        for track in medium.get('track-list', []):
            recording = track.get('recording', {})
            track_mbid = recording.get('id')
            track_uri = (f"https://musicbrainz.org/recording/{track_mbid}"
                         if track_mbid else None)
            # 'artist-credit-phrase' may not be returned by default,
            # but if you have it, we can store it:
            martist = recording.get('artist-credit-phrase', "")

            mb_tracks.append({
                "position": track.get("position"),
                "title": recording.get("title", ""),
                "uri": track_uri,
                "artist": martist
            })

    # Sort local tracks by (subdir, tracknumber)
    def track_sort_key(t):
        try:
            num = int(t["tracknumber"]) if t["tracknumber"] else 9999
        except ValueError:
            num = 9999
        return (t["subdir"], num)

    sorted_local_tracks = sorted(local_data["tracks"], key=track_sort_key)
    track_lines = []
    max_tracks = max(len(sorted_local_tracks), len(mb_tracks))

    for i in range(max_tracks):
        # Local side
        if i < len(sorted_local_tracks):
            lt = sorted_local_tracks[i]

            filename = lt.get('filename')
            if subdir := lt.get('subdir'):
                filename = f"{subdir}/{filename}"

            ln = lt.get("tracknumber", "")
            ltitle = lt.get("title", "")
            lartist = lt.get("artist", "")
            left_lines = [
                f"File:    {filename}",
                f"Track#:  {ln}",
                f"Title:   {ltitle}",
                f"Artist:  {lartist}"
            ]
        else:
            left_lines = ["(No local track)", "", ""]

        # MB side
        if i < len(mb_tracks):
            mt = mb_tracks[i]
            mn = mt.get("position", "")
            mtitle = mt.get("title", "")
            martist = mt.get("artist", "")
            muri = mt.get("uri", "")
            right_lines = [
                f"URI:     {muri if muri else '(no MB URI)'}",
                f"Track#:  {mn}",
                f"Title:   {mtitle}",
                f"Artist:  {martist}",
            ]
            print(right_lines)
        else:
            right_lines = ["(No MB track)", "", ""]

        # Merge them side-by-side (with unify_if_identical=True)
        chunk = side_by_side_format(left_lines, right_lines,
                                    left_width=60, unify_if_identical=True)
        track_lines.extend(chunk)
        track_lines.append("-" * 120)  # separator

    # Combine everything
    output = []
    output.append("=" * 120)
    output.append("RELEASE-LEVEL COMPARISON")
    output.append("=" * 120)
    output.extend(release_info_diff)
    output.append("")
    output.append("=" * 120)
    output.append("TRACK-BY-TRACK COMPARISON")
    output.append("=" * 120)
    output.extend(track_lines)

    return "\n".join(output)


def main():
    """Main entry point."""
    args = parse_args()
    root_directory = args.root_directory

    # Guess from folder name
    base_name = os.path.basename(os.path.normpath(root_directory))
    guessed_artist, guessed_album = guess_artist_and_album_from_directory(base_name)

    # Gather local tracks (including Bonus Tracks subfolders, etc.)
    local_track_list = gather_all_local_tracks(root_directory)
    if not local_track_list:
        print(f"No audio tracks found in '{root_directory}'. Aborting.")
        sys.exit(1)

    # Create local data structure for diff
    local_data = {
        "artist": guessed_artist,
        "album": guessed_album,
        "tracks": local_track_list
    }

    # Query MusicBrainz for matching release
    mb_release = find_best_release_match(guessed_artist, guessed_album)
    if not mb_release:
        print(
            f"No matching MusicBrainz release found for "
            f"guessed artist='{guessed_artist}', album='{guessed_album}'."
        )
        sys.exit(0)

    # Produce side-by-side diff, unify identical lines
    diff_output = generate_side_by_side_diff(local_data, mb_release)
    print(diff_output)


if __name__ == "__main__":
    main()
