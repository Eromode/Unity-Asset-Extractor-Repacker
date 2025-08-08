# Unity Asset Extractor & Repacker

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Downloads](https://img.shields.io/badge/Downloads-1k%2B-brightgreen.svg)

A **single-file Python CLI tool** to **extract** and **repack** Unity asset bundles.  
Supports a wide range of asset types for extraction and selective types for repacking.  

---

## ✨ Features

- 📂 **Extract** 12+ Unity asset types:  
  `Texture2D`, `TextAsset`, `Mesh`, `AudioClip`, `Shader`, `MonoBehaviour`, `AnimationClip`, `Material`, `Sprite`, `Font`, `VideoClip`
- 🛠 **Repack** only supported types:  
  `Texture2D`, `TextAsset`, `Mesh`
- 📝 Output `.meta.json` metadata for each asset
- 📁 **Flat mode** (`--flat`) for single-folder output
- 🧪 **Dry-run mode** (`--dry-run`) to simulate actions
- 🗒 **Logging** to file with `--log`
- ⚡ Batch operations:  
  `extract-all` and `repack-all`

---

## 📦 Installation

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### Syntax
```bash
python main.py <command> <inputs> <output> [options]
```

### Commands
| Command        | Description |
|----------------|-------------|
| `extract`      | Extract a single bundle |
| `extract-all`  | Extract all bundles from a directory |
| `repack`       | Repack a single bundle |
| `repack-all`   | Repack all bundles from a directory |

---

### Options
| Option     | Type  | Description |
|------------|-------|-------------|
| `--type`   | List  | Asset types to process: `all`, `Texture2D`, `TextAsset`, `Mesh`, `AudioClip`, `Shader`, `MonoBehaviour`, `AnimationClip`, `Material`, `Sprite`, `Font`, `VideoClip` |
| `--flat`   | Flag  | Disable per-type subfolders in output |
| `--dry-run`| Flag  | Simulate actions without writing files |
| `--log`    | Path  | Save a log of processed assets to the given file path |

---

## 💡 Examples

**Extract Texture2D from a single bundle**
```bash
python main.py extract mybundle.bundle output_folder --type Texture2D
```

**Extract all assets from a directory**
```bash
python main.py extract-all /path/to/bundles extracted_output --type all
```

**Repack a single bundle**
```bash
python main.py repack original.bundle extracted_folder repacked.bundle --type all
```

**Repack all bundles from a directory**
```bash
python main.py repack-all original_bundles extracted_folders repacked_output --type Texture2D
```

**Extract AudioClip and Shader into a flat folder with logging**
```bash
python main.py extract mybundle.bundle output --type AudioClip Shader --flat --log extract.log
```

---

## 📄 Example Output

```
Extracting (['AudioClip', 'Shader']) ━━━━━━━━━━━━━━━━━━━━ 100% 50/50

Extracted:
  AudioClip: 5
  Shader: 3

Log written to extract.log
```

---

## 📝 Notes

- **Repacking** is intentionally limited to `Texture2D`, `TextAsset`, and `Mesh` for safety.
- `.meta.json` files are generated alongside each extracted asset for reference and integrity checks.
- This is a **single-file tool** for easy sharing — no packaging required.
- 🔍 For more advanced asset editing or complete unpacking of Unity projects, you may also want to try:
  - [AssetRipper](https://github.com/AssetRipper/AssetRipper) — Full Unity project export from asset bundles.
  - [UABEA (Unity Asset Bundle Extractor Avalonia)](https://github.com/nesrak1/UABEANext) — GUI-uabe for newer versions of unity.
---

## 📜 License

[MIT](LICENSE)
