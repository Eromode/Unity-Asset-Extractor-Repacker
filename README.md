# Unity Bundle Tool

A safe, Python-based modding pipeline for Unity `.bundle` files.  
This tool allows you to **unpack**, **modify**, **repack**, and **verify** Unity asset bundles without overwriting the originals.

## Features
- **Unpack** Unity bundles into textures and text assets
- **Batch processing** for multiple bundles
- **Safe repacking** with `modified_` prefix (originals remain untouched)
- **Asset verification** to detect missing or corrupted files
- **Automatic Unity version detection**
- **Modification history logging**

## Requirements
- Python 3.8+
- `UnityPy`
- `Pillow`
- `tqdm`

## Installation
```bash
git clone https://github.com/yourusername/unity-bundle-tool.git
cd unity-bundle-tool
pip install -r requirements.txt
```

## Usage

### General Syntax
```bash
python bundle_tool.py <command> [arguments] [options]
```

### Commands
| Command | Description |
|---------|-------------|
| `unpack <bundle_file>` | Extract assets from a single bundle |
| `batch-unpack <directory>` | Extract all `.bundle` files in a folder |
| `repack <bundle_file> [--fast]` | Create a modified bundle from an extracted folder |
| `batch-repack <directory> [--fast]` | Create modified bundles for all extracted/edited bundles |
| `verify <bundle_file>` | Check integrity of bundle assets |
| `history` | View the modification log |
| `help` | Show usage instructions |

### Options
- `--fast` → Disable compression for faster repacking  
- `--verbose` → Show detailed output

### Examples
```bash
# Unpack a single bundle
python bundle_tool.py unpack character.bundle

# Batch unpack all bundles in a folder
python bundle_tool.py batch-unpack ./assets

# Repack with compression
python bundle_tool.py repack character.bundle

# Fast repack without compression
python bundle_tool.py repack character.bundle --fast

# Verify bundle integrity
python bundle_tool.py verify character.bundle

# View modification history
python bundle_tool.py history
```

## Safety Features
- Original bundles are never modified
- Modified bundles are prefixed with `modified_`
- Changes are logged to `modifications.json`

## License
MIT License
