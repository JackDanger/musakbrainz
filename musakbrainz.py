#!/usr/bin/env python3
"""
A script that:
1) Recursively scans a local directory to find all audio files (including 'Bonus Tracks' subfolders).
2) Extracts metadata for each file (title, tracknumber, etc.) via mutagen.
3) Guesses the artist/album from the top-level directory name.
4) Looks up matching releases on MusicBrainz (musicbrainzngs) and finds the best release group by comparing total track counts.
5) Prints a side-by-side diff (left = local, right = MB) with "== " for identical lines in the center, using the chosen release.
6) Only offers to create new Release Groups (or open the Release edit page, etc.) if something is missing
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

# ---------------------------------------------------------------------------
# 1) MusicBrainz Setup
# ---------------------------------------------------------------------------
musicbrainzngs.set_useragent(
    "MusicBrainzSideBySideDiff",
    "0.1",
    "https://example.org/my-musicbrainz-app"
)


# ---------------------------------------------------------------------------
# 2) Utility / Argument Parsing
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Recursively gather local tracks, produce a side-by-side diff vs. MusicBrainz, matching the best release group by track count."
    )
    parser.add_argument("root_directory", help="Root directory of the album (subfolders included).")
    return parser.parse_args()


def prompt_yes_no(message):
    """Simple console prompt that returns True if user answers yes, else False."""
    while True:
        ans = input(f"{message} [y/N]? ").strip().lower()
        if ans in ('y', 'yes'):
            return True
        if ans in ('', 'n', 'no'):
            return False


def open_in_browser(url):
    """
    Cross-platform way to open a URL in the user’s default browser:
      - macOS:   'open <url>'
      - Linux:   'xdg-open <url>'
      - Windows: 'start <url>'
    """
    system = platform.system().lower()
    if 'darwin' in system:  # macOS
        subprocess.run(['open', url])
    elif 'windows' in system:
        subprocess.run(['start', url], shell=True)
    else:  # linux / other
        subprocess.run(['xdg-open', url])


# ---------------------------------------------------------------------------
# 3) Local File Gathering
# ---------------------------------------------------------------------------
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
    """Find all valid audio files under root_directory and parse track metadata."""
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


# ---------------------------------------------------------------------------
# 4) MusicBrainz Lookup + Diff
# ---------------------------------------------------------------------------
def get_mb_release_total_tracks(mb_release):
    """Return total # tracks across all mediums for a single MB release."""
    total = 0
    for medium in mb_release.get('medium-list', []):
        track_list = medium.get('track-list', [])
        total += len(track_list)
    return total


def get_best_release_for_rg(rg_releases, local_track_count):
    """
    Given multiple releases for the same release group,
    pick the single release whose track count is *closest* to local_track_count.
    Return (release_dict, diff).
    """
    best = None
    best_diff = None
    for r in rg_releases:
        count = get_mb_release_total_tracks(r)
        diff = abs(count - local_track_count)
        if best is None or diff < best_diff:
            best = r
            best_diff = diff
    return best, best_diff


def find_best_release_group(artist_name, album_name, local_track_count):
    """
    1) Search MusicBrainz for up to 10 releases matching artist_name + album_name.
    2) Bucket them by release-group ID.
    3) For each group, find the release that has the track count closest to local_track_count.
    4) Pick the group that yields the smallest difference. If there's a tie, ask user to choose.
    5) Return (best_release, best_release_group) or (None, None).

    'best_release' is the specific release we'll compare side-by-side.
    'best_release_group' is just the RG dictionary if we want it for reference.
    """
    # Step 1: search
    if not artist_name:
        result = musicbrainzngs.search_releases(release=album_name, limit=10)
    else:
        result = musicbrainzngs.search_releases(artist=artist_name, release=album_name, limit=10)
    found = result.get('release-list', [])
    if not found:
        return None, None

    # We'll fetch the full data for each release (including tracklists).
    # Group them by release-group ID => { rgid: [release_dicts], ... }
    groups = {}  # { rgid -> list of release_dicts }
    release_info = []
    for r in found:
        rid = r['id']
        try:
            full = musicbrainzngs.get_release_by_id(
                rid,
                includes=["artist-credits", "recordings", "release-groups", "labels", "url-rels"]
            )
            release_data = full["release"]
            # Extract RG ID
            rg = release_data.get("release-group")
            if not rg or "id" not in rg:
                # Possibly skip if no RG?
                # We'll treat "no RG" as distinct ID so we can store it anyway
                rgid = "NO_RG_" + rid  # or something unique
            else:
                rgid = rg["id"]
            groups.setdefault(rgid, []).append(release_data)
        except musicbrainzngs.WebServiceError:
            continue

    if not groups:
        return None, None

    # Step 2: For each RG, find best release for local track count
    rg_candidates = []  # list of (rgid, best_release_in_rg, best_diff_in_rg, release_group_dict)
    for rgid, releases_in_group in groups.items():
        # They presumably share the same "release-group" dict, so let's get that from the first
        rg_dict = releases_in_group[0].get("release-group", {})
        best_rel, best_diff = get_best_release_for_rg(releases_in_group, local_track_count)
        rg_candidates.append((rgid, best_rel, best_diff, rg_dict))

    # Step 3: sort by best_diff ascending
    rg_candidates.sort(key=lambda x: x[2])  # compare on best_diff

    # The top item(s) have the minimal difference
    min_diff = rg_candidates[0][2]
    best_list = [c for c in rg_candidates if c[2] == min_diff]

    if len(best_list) == 1:
        # Exactly one best RG
        rgid, best_rel, best_diff, rg_dict = best_list[0]
        return best_rel, rg_dict
    else:
        # We have multiple groups with the same difference. Prompt user to choose
        print(f"\nFound {len(best_list)} release groups with the same track-count difference={min_diff}:")
        for i, (rgid, best_rel, diff, rg_dict) in enumerate(best_list, start=1):
            # Summaries
            # Possibly show the RG title
            rg_title = rg_dict.get("title") if rg_dict else "(No RG Title)"
            # Show best_rel title, track count
            ccount = get_mb_release_total_tracks(best_rel)
            rel_title = best_rel.get("title", "(No release title)")
            rid = best_rel.get("id")
            # flatten artist credits
            ac_credits = best_rel.get("artist-credit", [])
            ac_names = []
            for cred in ac_credits:
                if isinstance(cred, dict) and 'artist' in cred:
                    ac_names.append(cred['artist']['name'])
                elif isinstance(cred, str):
                    ac_names.append(cred)
            ac_joined = " & ".join(ac_names) if ac_names else "(Unknown Artist)"

            print(f"{i}) RG: {rgid} '{rg_title}' => Release: {ac_joined} - {rel_title} [MBID={rid}] (Tracks={ccount})")

        while True:
            choice = input(f"Enter a number 1..{len(best_list)} or press Enter to cancel: ").strip()
            if not choice:
                return None, None
            try:
                idx = int(choice)
                if 1 <= idx <= len(best_list):
                    sel = best_list[idx - 1]
                    return sel[1], sel[3]  # best_rel, rg_dict
            except ValueError:
                pass
            print("Invalid choice. Try again.")


def side_by_side_format(lines_left, lines_right, left_width=60, unify_if_identical=True):
    """
    If lines match and are not empty, show "== line".
    Else side-by-side: left|right.
    """
    output = []
    max_len = max(len(lines_left), len(lines_right))
    for i in range(max_len):
        l = lines_left[i] if i < len(lines_left) else ""
        r = lines_right[i] if i < len(lines_right) else ""
        if unify_if_identical and l.strip() and (l == r):
            output.append(f"== {l}")
        else:
            output.append(f"{l:<{left_width}} | {r}")
    return output


def generate_side_by_side_diff(local_data, mb_data):
    """
    Show a release-level and track-level diff between local_data and mb_data (a single MB release).
    """
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


# ---------------------------------------------------------------------------
# 5) Open MB forms (release-group/create, release/add, release/<id>/edit) only if needed
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 6) Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()
    root_dir = args.root_directory
    base_name = os.path.basename(os.path.normpath(root_dir))
    guessed_artist, guessed_album = guess_artist_and_album_from_directory(base_name)

    # 1) Gather local tracks
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

    # 2) Find best matching release-group (and best release in that group)
    best_release, rg_dict = find_best_release_group(guessed_artist, guessed_album, local_track_count)
    if not best_release:
        print(f"\nNo MB release group found that matches artist='{guessed_artist}', album='{guessed_album}'.")
        # Possibly we want to create a new release group if truly none found
        if prompt_yes_no("No MB release group. Do you want to create a NEW Release Group?"):
            artist_mbid = input("Enter the Artist MBID (e.g. f4353d58-79ee-...)? ").strip()
            rg_name = guessed_album or "New ReleaseGroup"
            create_release_group_on_musicbrainz(artist_mbid, rg_name, primary_type_id=1)
        sys.exit(0)

    # 3) Show the side-by-side diff for that release
    diff_text = generate_side_by_side_diff(local_data, best_release)
    print(diff_text)

    # 4) Check if the release-group is set, or we might create one
    if rg_dict and "id" in rg_dict:
        rg_id = rg_dict["id"]
        rg_title = rg_dict.get("title", "")
        print(f"\nRelease belongs to Release-Group: {rg_id} ({rg_title})")
    else:
        # No RG in that release data; offer to create
        if prompt_yes_no("\nNo Release Group assigned. Do you want to create a new Release Group?"):
            artist_mbid = input("Artist MBID for the new release-group? ").strip()
            rg_name = guessed_album or "New RG"
            create_release_group_on_musicbrainz(artist_mbid, rg_name, primary_type_id=1)

    # 5) If local has more tracks than MB, offer to open the release edit page
    mb_track_count = get_mb_release_total_tracks(best_release)
    if local_track_count > mb_track_count:
        rid = best_release.get("id")
        print(f"\nIt seems you have {local_track_count} local tracks, but MB only has {mb_track_count}.")
        msg = ("Do you want to open the MB release edit page to fix/add missing tracks?\n"
               "NOTE: This is recommended ONLY if the official release truly matches your local version.\n"
               "Open release edit page now")
        if rid and prompt_yes_no(msg):
            open_release_edit_page(rid)

    print("\nDone. Exiting.")


if __name__ == "__main__":
    main()
