#!/usr/bin/env python3
"""
A script that:
1) Recursively scans a local directory to find all audio files (including 'Bonus Tracks' subfolders).
2) Extracts metadata for each file (title, tracknumber, etc.) via mutagen.
3) Guesses the artist/album from the top-level directory name.
4) Looks up matching release data on MusicBrainz (musicbrainzngs), tries to find the best match by track count.
5) Prints a side-by-side diff (left = local, right = MB) with "== " for identical lines in the center.
6) Only offers to create new Release Groups (or open the Release edit page, etc.) when something is missing
   or clearly mismatched, with explicit caution prompts to reduce accidental "yes."

Usage:
  python complete_script.py "/path/to/A Plus D - Best of Bootie Mashup 2024"
"""

import os
import sys
import argparse
import re
import platform
import subprocess
from urllib.parse import urlencode, quote_plus

import musicbrainzngs
from mutagen import File as MutagenFile


# ----------------------------------------------------------------------------
# 1) MusicBrainz Setup
# ----------------------------------------------------------------------------
musicbrainzngs.set_useragent(
    "MusicBrainzSideBySideDiff",
    "0.1",
    "https://example.org/my-musicbrainz-app"
)


# ----------------------------------------------------------------------------
# 2) Utility / Argument Parsing
# ----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Recursively gather local tracks, produce a side-by-side diff vs. MusicBrainz, selectively open MB forms."
    )
    parser.add_argument("root_directory", help="Root directory of the album (subfolders included).")
    return parser.parse_args()


def prompt_yes_no(message):
    """
    Simple console prompt that returns True if user answers yes (y/yes).
    Default is No if user hits enter or types n/no.
    """
    while True:
        ans = input(f"{message} [y/N]? ").strip().lower()
        if ans in ('y', 'yes'):
            return True
        if ans in ('', 'n', 'no'):
            return False


def open_in_browser(url):
    """
    Cross-platform way to open a URL in the user’s default browser.
      - macOS:    'open <url>'
      - Linux:    'xdg-open <url>'
      - Windows:  'start <url>'
    """
    system = platform.system().lower()
    if 'darwin' in system:  # macOS
        subprocess.run(['open', url])
    elif 'windows' in system:
        subprocess.run(['start', url], shell=True)
    else:  # linux / other
        subprocess.run(['xdg-open', url])


# ----------------------------------------------------------------------------
# 3) Local File Gathering
# ----------------------------------------------------------------------------
VALID_AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg"}


def guess_artist_and_album_from_directory(dir_name):
    """
    Naive approach: parse "Artist - Album" from the directory name.
    If that fails, treat entire name as album.
    """
    pattern = r"^(.*?)\s*-\s*(.*)$"
    match = re.match(pattern, dir_name)
    if match:
        artist, album = match.groups()
        return artist.strip(), album.strip()
    return None, dir_name.strip()


def find_audio_files_recursively(root_directory):
    for dirpath, dirnames, filenames in os.walk(root_directory):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for fname in sorted(filenames):
            if fname.startswith('.'):
                continue
            ext = os.path.splitext(fname.lower())[1]
            if ext in VALID_AUDIO_EXTENSIONS:
                yield os.path.join(dirpath, fname)


def extract_tags_from_file(file_path):
    audio_data = {
        "title": None,
        "artist": None,
        "tracknumber": None,
    }
    audio = MutagenFile(file_path)
    if not audio or not audio.tags:
        return audio_data

    tags = dict(audio.tags)

    for key in ['TIT2', 'TITLE', '\xa9nam']:
        if key in tags:
            audio_data['title'] = str(tags[key])
            break

    for key in ['TPE1', 'ARTIST', '\xa9ART']:
        if key in tags:
            audio_data['artist'] = str(tags[key])
            break

    for key in ['TRCK', 'TRACKNUMBER']:
        if key in tags:
            raw = str(tags[key])
            audio_data['tracknumber'] = raw.split('/')[0]
            break

    return audio_data


def gather_all_local_tracks(root_directory):
    root_directory = os.path.abspath(root_directory)
    all_tracks = []

    for audio_path in find_audio_files_recursively(root_directory):
        rel_path = os.path.relpath(audio_path, root_directory)
        subdir = os.path.dirname(rel_path) or ""
        if subdir == ".":
            subdir = ""

        meta = extract_tags_from_file(audio_path)
        if not meta['title']:
            meta['title'] = os.path.splitext(os.path.basename(audio_path))[0]

        track_info = {
            "full_path": audio_path,
            "subdir": subdir,
            "filename": os.path.basename(audio_path),
            "title": meta["title"],
            "artist": meta["artist"],
            "tracknumber": meta["tracknumber"],
        }
        all_tracks.append(track_info)

    return all_tracks


# ----------------------------------------------------------------------------
# 4) MusicBrainz Lookup + Diff
# ----------------------------------------------------------------------------
def get_mb_release_total_tracks(mb_release):
    """
    Given a MusicBrainz release dict from get_release_by_id(...),
    return the sum of all track counts across all mediums.
    """
    total = 0
    for medium in mb_release.get('medium-list', []):
        track_list = medium.get('track-list', [])
        total += len(track_list)
    return total


def find_best_release_match(artist_name, album_name, local_track_count):
    """
    1) Search MB for up to 10 releases that match artist_name and album_name.
    2) For each release, get detailed data (including track lists).
    3) Compare total track count to local_track_count.
    4) Pick the release with the smallest difference in track count.
       If multiple releases tie, prompt the user which one to pick.
    5) Return the chosen release dict or None if none found.
    """
    # Step 1: search for releases
    if not artist_name:
        result = musicbrainzngs.search_releases(release=album_name, limit=10)
    else:
        result = musicbrainzngs.search_releases(artist=artist_name, release=album_name, limit=10)
    releases = result.get('release-list', [])
    if not releases:
        return None

    # We'll gather (release_id -> difference in track count)
    candidate_info = []  # list of tuples: (release_dict, track_count_diff)
    for r in releases:
        release_id = r['id']
        try:
            # Step 2: fetch detailed data
            full = musicbrainzngs.get_release_by_id(
                release_id,
                includes=["artist-credits", "recordings", "url-rels", "labels", "release-groups"]
            )
            release_data = full["release"]

            # Step 3: compare track counts
            remote_count = get_mb_release_total_tracks(release_data)
            diff = abs(remote_count - local_track_count)
            candidate_info.append((release_data, diff))
        except musicbrainzngs.WebServiceError:
            continue

    if not candidate_info:
        return None

    # Step 4: pick release with smallest difference
    candidate_info.sort(key=lambda x: x[1])  # sort by diff ascending
    best_diff = candidate_info[0][1]

    # gather all releases that share that best_diff
    best_matches = [c for c in candidate_info if c[1] == best_diff]

    if len(best_matches) == 1:
        # Exactly one best match
        return best_matches[0][0]
    else:
        # multiple matches have the same track-count difference
        print(f"\nFound {len(best_matches)} potential releases with the same track-count difference={best_diff}:")
        for idx, (rel, diffval) in enumerate(best_matches, start=1):
            rid = rel.get('id')
            total_remote = get_mb_release_total_tracks(rel)
            artist_credit = rel.get('artist-credit', [])
            # Flatten artist name(s)
            ac_names = []
            for cred in artist_credit:
                if isinstance(cred, dict) and 'artist' in cred:
                    ac_names.append(cred['artist']['name'])
                elif isinstance(cred, str):
                    ac_names.append(cred)
            ac_joined = " & ".join(ac_names) if ac_names else "(Unknown Artist)"
            title = rel.get('title', '(Unknown Title)')
            print(f"{idx}) {ac_joined} - {title} [MBID={rid}]  (Tracks={total_remote})")

        # prompt user
        while True:
            choice = input(f"Enter a number 1..{len(best_matches)}, or press Enter to cancel: ").strip()
            if not choice:
                return None
            try:
                idx = int(choice)
                if 1 <= idx <= len(best_matches):
                    return best_matches[idx - 1][0]
            except ValueError:
                pass
            print("Invalid choice. Please try again.")


def side_by_side_format(lines_left, lines_right, left_width=60, unify_if_identical=True):
    """
    If lines match and are not empty, show "    == line".
    Else side-by-side: left|right.
    """
    output = []
    max_len = max(len(lines_left), len(lines_right))
    for i in range(max_len):
        l = lines_left[i] if i < len(lines_left) else ""
        r = lines_right[i] if i < len(lines_right) else ""
        if unify_if_identical and l.strip() and (l == r):
            output.append(f"  == {l}")
        else:
            output.append(f"{l:<{left_width}} | {r}")
    return output


def generate_side_by_side_diff(local_data, mb_data):
    local_artist = local_data["artist"] or "Unknown Local Artist"
    local_album = local_data["album"] or "Unknown Local Album"
    local_rlines = [
        f"Artist: {local_artist}",
        f"Album:  {local_album}",
        "(subdir logic not shown at release-level)"
    ]

    mb_rlines = []
    mb_artists = []
    for credit in mb_data.get('artist-credit', []):
        if isinstance(credit, dict) and "artist" in credit:
            mb_artists.append(credit["artist"]["name"])
        elif isinstance(credit, str):
            mb_artists.append(credit)
    joined = " & ".join(mb_artists) if mb_artists else "Unknown MB Artist"
    mb_rlines.append(f"Artist: {joined}")

    mb_album = mb_data.get("title", "Unknown MB Album")
    mb_rlines.append(f"Album:  {mb_album}")

    if 'id' in mb_data:
        rid = mb_data['id']
        mb_rlines.append(f"MB Release URI: https://musicbrainz.org/release/{rid}")

    for urlrel in mb_data.get("url-relation-list", []):
        rtype = urlrel.get('type')
        tgt = urlrel.get('target')
        mb_rlines.append(f" - {rtype}: {tgt}")

    # Release-level diff
    release_diff = side_by_side_format(local_rlines, mb_rlines, 60, True)

    # Track-level
    mb_tracks = []
    for medium in mb_data.get('medium-list', []):
        for track in medium.get('track-list', []):
            rec = track.get('recording', {})
            mbid = rec.get('id')
            track_uri = f"https://musicbrainz.org/recording/{mbid}" if mbid else None
            artist_phrase = rec.get('artist-credit-phrase', "")
            mb_tracks.append({
                "position": track.get("position"),
                "title": rec.get("title", ""),
                "uri": track_uri,
                "artist": artist_phrase
            })

    # Sort local
    def track_sort_key(t):
        try:
            num = int(t["tracknumber"]) if t["tracknumber"] else 9999
        except ValueError:
            num = 9999
        return (t["subdir"], num)

    sorted_local = sorted(local_data["tracks"], key=track_sort_key)
    track_lines = []
    max_t = max(len(sorted_local), len(mb_tracks))

    for i in range(max_t):
        if i < len(sorted_local):
            lt = sorted_local[i]
            fname = lt["filename"]
            if lt["subdir"]:
                fname = f"{lt['subdir']}/{fname}"
            ln = lt["tracknumber"] or ""
            ltitle = lt["title"] or ""
            lartist = lt["artist"] or ""
            left_chunk = [
                f"File:    {fname}",
                f"Track#:  {ln}",
                f"Title:   {ltitle}",
                f"Artist:  {lartist}"
            ]
        else:
            left_chunk = ["(No local track)", "", "", ""]

        if i < len(mb_tracks):
            mt = mb_tracks[i]
            muri = mt["uri"] or "(no MB URI)"
            mn = mt["position"] or ""
            mtitle = mt["title"] or ""
            martist = mt["artist"] or ""
            right_chunk = [
                f"URI:     {muri}",
                f"Track#:  {mn}",
                f"Title:   {mtitle}",
                f"Artist:  {martist}"
            ]
        else:
            right_chunk = ["(No MB track)", "", "", ""]

        chunk = side_by_side_format(left_chunk, right_chunk, 60, True)
        track_lines.extend(chunk)
        track_lines.append("-" * 120)

    out = []
    out.append("=" * 120)
    out.append("RELEASE-LEVEL COMPARISON")
    out.append("=" * 120)
    out.extend(release_diff)
    out.append("")
    out.append("=" * 120)
    out.append("TRACK-BY-TRACK COMPARISON")
    out.append("=" * 120)
    out.extend(track_lines)
    return "\n".join(out)


# ----------------------------------------------------------------------------
# 5) Open MB forms (release-group/create, release/add, release/<id>/edit) only if needed
# ----------------------------------------------------------------------------
def create_release_group_on_musicbrainz(artist_mbid, rg_name, primary_type_id=1):
    """
    e.g. https://musicbrainz.org/release-group/create?artist=<artist_mbid>
         &edit-release-group.name=<rg_name>&edit-release-group.primary_type_id=1
    """
    base = "https://musicbrainz.org/release-group/create"
    params = {
        "artist": artist_mbid,
        "edit-release-group.name": rg_name,
        "edit-release-group.primary_type_id": str(primary_type_id)  # 1=Album,2=Single,3=EP
    }
    q = urlencode(params, quote_via=quote_plus)
    url = f"{base}?{q}"
    print(f"Opening Release Group create form:\n  {url}")
    open_in_browser(url)


def create_release_on_musicbrainz(rg_mbid):
    """
    e.g. https://musicbrainz.org/release/add?release-group=<rg_mbid>
    """
    base = "https://musicbrainz.org/release/add"
    q = urlencode({"release-group": rg_mbid}, quote_via=quote_plus)
    url = f"{base}?{q}"
    print(f"Opening Release create form:\n  {url}")
    open_in_browser(url)


def open_release_edit_page(release_mbid):
    """
    e.g. https://musicbrainz.org/release/<release_mbid>/edit
    """
    url = f"https://musicbrainz.org/release/{release_mbid}/edit"
    print(f"Opening Release edit page:\n  {url}")
    open_in_browser(url)


# ----------------------------------------------------------------------------
# 6) Main
# ----------------------------------------------------------------------------
def main():
    args = parse_args()
    root_dir = args.root_directory
    base_name = os.path.basename(os.path.normpath(root_dir))
    guessed_artist, guessed_album = guess_artist_and_album_from_directory(base_name)

    local_tracks = gather_all_local_tracks(root_dir)
    if not local_tracks:
        print(f"No audio tracks found in '{root_dir}'. Aborting.")
        sys.exit(1)

    local_data = {
        "artist": guessed_artist,
        "album": guessed_album,
        "tracks": local_tracks
    }
    local_track_count = len(local_tracks)

    # 1) Attempt to find best MB release by track count
    mb_release = find_best_release_match(guessed_artist, guessed_album, local_track_count)
    if not mb_release:
        # No release found or user canceled tie selection
        print(f"No MB release found for artist='{guessed_artist}', album='{guessed_album}'.")

        # Possibly we want to create a new release group if truly none found
        if prompt_yes_no("No MB release. Do you want to create a NEW Release Group?"):
            artist_mbid = input("Enter the Artist MBID (e.g. f4353d58-79ee-...)? ").strip()
            rg_name = guessed_album or "New ReleaseGroup"
            create_release_group_on_musicbrainz(artist_mbid, rg_name, primary_type_id=1)

        sys.exit(0)

    # 2) If we found a release, show the diff
    diff_text = generate_side_by_side_diff(local_data, mb_release)
    print(diff_text)

    # 3) Check if there's a release group
    rg = mb_release.get("release-group")
    if not rg or "id" not in rg:
        # No release-group found. Possibly we ask if user wants to create one.
        if prompt_yes_no("\nNo Release Group assigned. Do you want to create a new Release Group?"):
            artist_mbid = input("Artist MBID for the new release-group? ").strip()
            rg_name = guessed_album or "New RG"
            create_release_group_on_musicbrainz(artist_mbid, rg_name, primary_type_id=1)
    else:
        # We do have a release-group
        rg_id = rg["id"]
        rg_title = rg.get("title", "")
        print(f"\nRelease has Release-Group: {rg_id} ({rg_title})")

    # 4) Check for track mismatches
    mb_track_count = get_mb_release_total_tracks(mb_release)
    if local_track_count > mb_track_count:
        rid = mb_release.get("id")
        print(f"\nIt seems you have {local_track_count} local tracks, but MB only has {mb_track_count}.")
        msg = ("Do you want to open the MB release edit page to fix/add missing tracks?\n"
               "NOTE: This is recommended ONLY if the official release truly matches your local version.\n"
               "Open release edit page now")
        if rid and prompt_yes_no(msg):
            open_release_edit_page(rid)

    print("\nDone. Exiting.")


if __name__ == "__main__":
    main()
