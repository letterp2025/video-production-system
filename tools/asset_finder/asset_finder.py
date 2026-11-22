#!/usr/bin/env python3
"""Search openly licensed media and download selected items with a source receipt."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_USER_AGENT = "VideoProductionSystem-AssetFinder/0.1 (local media research tool)"
OPENVERSE_BASE = "https://api.openverse.org/v1"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MAX_DOWNLOAD_BYTES_DEFAULT = 500 * 1024 * 1024

EXTENSIONS = {
    "image": {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"},
    "audio": {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".opus", ".wav"},
    "video": {".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".ogv", ".webm"},
}
MIME_SUFFIXES = {
    "image/avif": ".avif",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/tiff": ".tif",
    "image/webp": ".webp",
    "audio/aiff": ".aiff",
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "application/ogg": ".ogg",
    "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
    "video/ogg": ".ogv",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


class AssetFinderError(Exception):
    """Expected provider, metadata, or download error."""


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": API_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        raise AssetFinderError(f"Provider returned HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AssetFinderError(f"Could not read provider response: {exc}") from exc


def request_binary(
    url: str, target: Path, max_bytes: int, expected_media: str
) -> tuple[int, str, str]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "*/*", "User-Agent": API_USER_AGENT},
    )
    total = 0
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = urllib.parse.urlparse(response.geturl())
            if final_url.scheme != "https" or not final_url.netloc:
                raise AssetFinderError("Download redirected to a non-HTTPS or invalid URL.")
            content_type = response.headers.get_content_type().lower()
            content_main_type = content_type.split("/", 1)[0]
            generic_types = {"application/octet-stream", "application/x-download", "binary/octet-stream"}
            if content_type == "application/ogg" and expected_media == "audio":
                pass
            elif content_type not in generic_types and content_main_type != expected_media:
                raise AssetFinderError(
                    f"Provider returned {content_type}, which does not match expected {expected_media} media."
                )
            length = response.headers.get("Content-Length")
            if length:
                try:
                    declared_length = int(length)
                except ValueError as exc:
                    raise AssetFinderError("Provider returned an invalid Content-Length.") from exc
                if declared_length > max_bytes:
                    raise AssetFinderError(
                        f"File declares {declared_length} bytes; limit is {max_bytes}."
                    )
            with target.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise AssetFinderError(
                            f"Download exceeded the {max_bytes}-byte safety limit."
                        )
                    digest.update(chunk)
                    output.write(chunk)
            return total, content_type, digest.hexdigest()
    except AssetFinderError:
        target.unlink(missing_ok=True)
        raise
    except urllib.error.HTTPError as exc:
        target.unlink(missing_ok=True)
        body = exc.read(1000).decode("utf-8", errors="replace")
        raise AssetFinderError(f"Download failed with HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        target.unlink(missing_ok=True)
        raise AssetFinderError(f"Download failed: {exc}") from exc
    except Exception:
        target.unlink(missing_ok=True)
        raise


def strip_markup(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]*>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def openverse_search(media: str, query: str, limit: int) -> list[dict[str, Any]]:
    endpoint = f"{OPENVERSE_BASE}/{ 'images' if media == 'image' else 'audio' }/"
    params = urllib.parse.urlencode({"q": query, "page_size": limit})
    payload = request_json(f"{endpoint}?{params}")
    results = []
    for item in payload.get("results", []):
        asset_id = str(item.get("id", ""))
        if not asset_id:
            continue
        results.append(
            {
                "provider": f"openverse-{media}",
                "ref": f"openverse-{media}:{asset_id}",
                "id": asset_id,
                "media": media,
                "title": strip_markup(item.get("title")) or "Untitled",
                "creator": strip_markup(item.get("creator")) or "Creator not listed",
                "license": strip_markup(item.get("license")) or "License not listed",
                "license_version": strip_markup(item.get("license_version")),
                "license_url": item.get("license_url", ""),
                "attribution": strip_markup(item.get("attribution")),
                "source_page": item.get("foreign_landing_url", ""),
                "download_url": item.get("url", ""),
                "filetype": strip_markup(item.get("filetype")),
            }
        )
    return results


def commons_search(media: str, query: str, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": query,
            "gsrlimit": str(min(50, max(limit * 3, limit))),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "360",
            "maxlag": "5",
        }
    )
    payload = request_json(f"{COMMONS_API}?{params}")
    pages = payload.get("query", {}).get("pages", [])
    results = []
    for page in pages:
        page_id = str(page.get("pageid", ""))
        title = str(page.get("title", "File without title"))
        suffix = Path(title).suffix.lower()
        if suffix not in EXTENSIONS[media]:
            continue
        infos = page.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        metadata = info.get("extmetadata", {})

        def field(name: str) -> str:
            return strip_markup(metadata.get(name, {}).get("value", ""))

        results.append(
            {
                "provider": "wikimedia",
                "ref": f"wikimedia:{page_id}",
                "id": page_id,
                "media": media,
                "title": title.removeprefix("File:"),
                "creator": field("Artist") or field("Credit") or "Creator not listed",
                "license": field("LicenseShortName") or "License not listed",
                "license_version": "",
                "license_url": field("LicenseUrl"),
                "attribution": field("Attribution") or field("Credit"),
                "source_page": info.get("descriptionurl", ""),
                "download_url": info.get("url", ""),
                "filetype": suffix.lstrip("."),
            }
        )
        if len(results) >= limit:
            break
    return results


def print_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No results returned.")
        return
    for index, item in enumerate(results, 1):
        print(f"{index}. {item['ref']} [{item['media']}]")
        print(f"   {item['title']}")
        print(f"   Creator: {item['creator']}")
        print(f"   License: {item['license']} {item.get('license_version', '')}".rstrip())
        for flag in license_flags(item):
            print(f"   {flag}")
        print(f"   Source: {item['source_page']}")
        if item.get("attribution"):
            print(f"   Credit: {item['attribution']}")
        print()


def license_flags(asset: dict[str, Any]) -> list[str]:
    license_name = str(asset.get("license", "")).strip()
    normalized = license_name.lower()
    flags = []
    if not license_name or "not listed" in normalized:
        flags.append("FLAG: license is missing; treat this result as unverified.")
    if "non-commercial" in normalized or "noncommercial" in normalized or re.search(
        r"(?:^|[-_\s])nc(?:$|[-_\s\d])", normalized
    ):
        flags.append("FLAG: non-commercial restriction indicated; not cleared for monetized use.")
    if "no-derivatives" in normalized or "no derivatives" in normalized or re.search(
        r"(?:^|[-_\s])nd(?:$|[-_\s\d])", normalized
    ):
        flags.append("FLAG: no-derivatives term indicated; check whether the planned video use is permitted.")
    return flags


def commons_detail(page_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "pageids": page_id,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
        }
    )
    payload = request_json(f"{COMMONS_API}?{params}")
    pages = payload.get("query", {}).get("pages", [])
    if not pages or not pages[0].get("imageinfo"):
        raise AssetFinderError(f"Wikimedia file page {page_id} no longer has a downloadable file.")
    page = pages[0]
    info = page["imageinfo"][0]
    metadata = info.get("extmetadata", {})

    def field(name: str) -> str:
        return strip_markup(metadata.get(name, {}).get("value", ""))

    title = str(page.get("title", f"commons-{page_id}"))
    suffix = Path(title).suffix.lower()
    media = next((kind for kind, values in EXTENSIONS.items() if suffix in values), "unknown")
    return {
        "provider": "wikimedia",
        "id": page_id,
        "media": media,
        "title": title.removeprefix("File:"),
        "creator": field("Artist") or field("Credit") or "Creator not listed",
        "license": field("LicenseShortName") or "License not listed",
        "license_version": "",
        "license_url": field("LicenseUrl"),
        "attribution": field("Attribution") or field("Credit"),
        "source_page": info.get("descriptionurl", ""),
        "download_url": info.get("url", ""),
        "filetype": suffix.lstrip("."),
    }


def openverse_detail(media: str, asset_id: str) -> dict[str, Any]:
    endpoint_type = "images" if media == "image" else "audio"
    payload = request_json(f"{OPENVERSE_BASE}/{endpoint_type}/{urllib.parse.quote(asset_id, safe='')}/")
    return {
        "provider": "openverse",
        "id": asset_id,
        "media": media,
        "title": strip_markup(payload.get("title")) or "Untitled",
        "creator": strip_markup(payload.get("creator")) or "Creator not listed",
        "license": strip_markup(payload.get("license")) or "License not listed",
        "license_version": strip_markup(payload.get("license_version")),
        "license_url": payload.get("license_url", ""),
        "attribution": strip_markup(payload.get("attribution")),
        "source_page": payload.get("foreign_landing_url", ""),
        "download_url": payload.get("url", ""),
        "filetype": strip_markup(payload.get("filetype")),
    }


def safe_filename(value: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    name = re.sub(r"\s+", " ", name).strip(" .")
    name = (name or "asset")[:120]
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", name, re.IGNORECASE):
        name = f"_{name}"
    return name


def extension_for(asset: dict[str, Any], content_type: str = "") -> str:
    path_suffix = Path(urllib.parse.urlparse(asset.get("download_url", "")).path).suffix.lower()
    media = asset.get("media", "")
    if path_suffix in EXTENSIONS.get(media, set()):
        return path_suffix
    filetype = str(asset.get("filetype", "")).lower().lstrip(".")
    candidate = f".{filetype}" if filetype else ""
    if candidate in EXTENSIONS.get(media, set()):
        return candidate
    suffix = MIME_SUFFIXES.get(content_type.lower())
    if suffix in EXTENSIONS.get(media, set()):
        return suffix
    guessed, _ = mimetypes.guess_type(asset.get("download_url", ""))
    if guessed == content_type.lower():
        guess_suffix = Path(asset.get("download_url", "")).suffix.lower()
        if guess_suffix in EXTENSIONS.get(media, set()):
            return guess_suffix
    raise AssetFinderError(
        f"Could not determine a supported file extension for {media or 'unknown media'} "
        f"(provider filetype: {filetype or 'unknown'}, MIME type: {content_type or 'unknown'})."
    )


def get_asset(reference: str) -> dict[str, Any]:
    provider, separator, asset_id = reference.partition(":")
    if not separator or not asset_id:
        raise AssetFinderError("Reference must look like openverse-image:<id>, openverse-audio:<id>, or wikimedia:<page-id>.")
    if provider == "wikimedia":
        return commons_detail(asset_id)
    if provider in {"openverse-image", "openverse-audio"}:
        media = "image" if provider == "openverse-image" else "audio"
        return openverse_detail(media, asset_id)
    raise AssetFinderError(f"Unsupported download provider: {provider}")


def download_asset(args: argparse.Namespace) -> None:
    asset = get_asset(args.ref)
    print(f"Title: {asset['title']}")
    print(f"Creator: {asset['creator']}")
    print(f"License: {asset['license']} {asset.get('license_version', '')}".rstrip())
    for flag in license_flags(asset):
        print(flag)
    print(f"License URL: {asset.get('license_url') or 'not listed'}")
    print(f"Source page: {asset.get('source_page') or 'not listed'}")
    print(f"Attribution: {asset.get('attribution') or 'not listed'}")
    if not args.reviewed_terms:
        raise AssetFinderError(
            "Review the source page and license, then rerun with --reviewed-terms to download this selected item."
        )
    download_url = asset.get("download_url")
    if not download_url:
        raise AssetFinderError("Provider did not return a file URL.")
    parsed = urllib.parse.urlparse(download_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssetFinderError("Refusing a non-HTTPS or invalid provider file URL.")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    initial_extension = extension_for(asset)
    title = str(asset["title"])
    if Path(title).suffix.lower() in EXTENSIONS.get(asset["media"], set()):
        title = Path(title).stem
    base_name = safe_filename(title)
    file_path = output_dir / f"{base_name}{initial_extension}"
    if file_path.exists():
        raise AssetFinderError(f"Refusing to overwrite existing file: {file_path}")
    part_path = file_path.with_name(file_path.name + ".part")
    if part_path.exists():
        raise AssetFinderError(f"Partial file already exists; inspect it before retrying: {part_path}")

    size, content_type, sha256 = request_binary(
        download_url, part_path, args.max_mib * 1024 * 1024, asset["media"]
    )
    actual_extension = extension_for(asset, content_type)
    if actual_extension != initial_extension:
        corrected_path = output_dir / f"{base_name}{actual_extension}"
        if corrected_path.exists():
            part_path.unlink(missing_ok=True)
            raise AssetFinderError(f"Refusing to overwrite existing file: {corrected_path}")
        file_path = corrected_path
    part_path.replace(file_path)

    receipt = {
        "provider": asset["provider"],
        "provider_id": asset["id"],
        "media_type": asset["media"],
        "title": asset["title"],
        "creator": asset["creator"],
        "source_page": asset["source_page"],
        "license": asset["license"],
        "license_flags": license_flags(asset),
        "license_version": asset.get("license_version", ""),
        "license_url": asset["license_url"],
        "attribution": asset["attribution"],
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_file": file_path.name,
        "size_bytes": size,
        "content_type": content_type,
        "sha256": sha256,
        "terms_review_confirmed_by_user": True,
        "note": "The receipt preserves provider metadata; it is not a legal clearance or a guarantee of third-party rights.",
    }
    receipt_path = file_path.with_name(file_path.name + ".asset.json")
    try:
        with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    print(f"Downloaded: {file_path}")
    print(f"Receipt: {receipt_path}")
    print(f"Size: {size} bytes; SHA-256: {sha256}")


def read_sources() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("sources.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))["sources"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise AssetFinderError(f"Could not read source catalog {path}: {exc}") from exc


def print_sources() -> None:
    for source in read_sources():
        media = ", ".join(source["media_types"])
        print(f"{source['id']} [{source['status']}] - {media}")
        print(f"  {source['search_url']}")
        print(f"  Credentials: {source['credentials']}")
        print(f"  Terms: {source['terms_url']}")
        print(f"  {source['notes']}")


def search_assets(args: argparse.Namespace) -> None:
    providers = []
    if args.provider in {"all", "openverse"} and args.media in {"image", "audio"}:
        providers.append(("Openverse", lambda: openverse_search(args.media, args.query, args.limit)))
    if args.provider in {"all", "wikimedia"}:
        providers.append(("Wikimedia Commons", lambda: commons_search(args.media, args.query, args.limit)))
    if not providers:
        raise AssetFinderError(
            f"No implemented search provider supports media type '{args.media}' with provider '{args.provider}'."
        )
    combined = []
    failed = 0
    for name, search_fn in providers:
        try:
            combined.extend(search_fn())
        except AssetFinderError as exc:
            failed += 1
            print(f"Warning: {name} search failed: {exc}", file=sys.stderr)
    if failed == len(providers):
        raise AssetFinderError("All selected search providers failed. Check the warnings and retry later.")
    print_results(combined[: args.limit * len(providers)])
    print("Review the original item page and current license before download or publication.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find openly licensed media from Openverse and Wikimedia Commons; download only selected items."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sources", help="List known sources and their integration status.")

    search_parser = subparsers.add_parser("search", help="Search implemented providers.")
    search_parser.add_argument("query", help="Search terms, for example: abstract blue background")
    search_parser.add_argument("--media", choices=("image", "audio", "video"), required=True)
    search_parser.add_argument("--provider", choices=("all", "openverse", "wikimedia"), default="all")
    search_parser.add_argument("--limit", type=int, default=5, help="Maximum results per provider (1-20).")

    download_parser = subparsers.add_parser("download", help="Download one chosen result and write a metadata receipt.")
    download_parser.add_argument("--ref", required=True, help="Provider reference printed by search.")
    download_parser.add_argument("--output-dir", required=True, help="Local destination, preferably the video project's assets folder.")
    download_parser.add_argument("--max-mib", type=int, default=500, help="Maximum download size in MiB (default: 500).")
    download_parser.add_argument(
        "--reviewed-terms",
        action="store_true",
        help="Confirm that you reviewed the original source page and license before downloading.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "sources":
            print_sources()
            return 0
        if args.command == "search":
            if not 1 <= args.limit <= 20:
                raise AssetFinderError("--limit must be between 1 and 20.")
            search_assets(args)
            return 0
        if args.command == "download":
            if args.max_mib < 1:
                raise AssetFinderError("--max-mib must be at least 1.")
            download_asset(args)
            return 0
        parser.error("Unknown command")
    except AssetFinderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
