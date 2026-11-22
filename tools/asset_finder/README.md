# Asset Finder

Search Openverse and Wikimedia Commons, inspect a selected result, and download it with a neighboring JSON receipt containing the source and license metadata.

## Requirements

- Python 3.10 or newer
- Python standard library only
- Internet connection for provider search and download

## Search

    python tools/asset_finder/asset_finder.py search "abstract blue background" --media image --provider all --limit 5

Supported media types are image, audio, and video. Providers currently implemented are Openverse and Wikimedia Commons. The configured source URLs and terms links are in sources.json.

Each result has a short reference value. Open the original item page and review its current license, attribution requirements, and any separate rights in people, brands, music, or property before downloading.

## Download a reviewed result

    python tools/asset_finder/asset_finder.py download --ref PROVIDER-REFERENCE --output-dir path/to/project/assets/visuals --reviewed-terms

The command requests fresh provider metadata, requires the explicit --reviewed-terms flag, enforces HTTPS and a default 500 MiB size ceiling, avoids overwriting an existing file, and writes a .asset.json receipt with item metadata and a SHA-256 digest. Use --max-mib to change the ceiling.

The receipt records the review confirmation supplied by the operator. It does not make a legal determination or guarantee that the item is suitable for a particular use.

## Important limits

- Openverse is a discovery index. Confirm the specific source page and license.
- Wikimedia Commons licenses and metadata vary by item. Review each file page.
- The tool does not implement providers that require API keys.
- A search result may contain third-party rights that are not resolved by its license label.
- Keep downloaded media with the owning video project and record its source, creator, license, attribution, intended use, and changes. Do not add downloaded media to this repository.