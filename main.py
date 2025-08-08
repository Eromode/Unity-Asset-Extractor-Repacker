import os
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
import UnityPy
from tqdm import tqdm
from PIL import Image

# ------------------- Utility Functions -------------------
def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w.\- ]', '', name).strip()

def get_object_name(data, obj_type: str, path_id: int) -> str:
    for attr in ("name", "m_Name", "m_ClassName"):
        if hasattr(data, attr):
            val = getattr(data, attr)
            if isinstance(val, str) and val.strip():
                return sanitize_filename(val)
    return f"{obj_type}_{path_id}"

def should_process_type(obj_type: str) -> bool:
    if "all" in args.type:
        return True
    return obj_type in args.type

def write_text_file(path, content):
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(content)

def write_json_file(path, data):
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        json.dump(data, f, indent=2)

def write_binary_file(path, data_bytes):
    with open(path, "wb") as f:
        f.write(data_bytes)

# ------------------- CLI Setup -------------------
parser = argparse.ArgumentParser(description="Unity Asset Extractor/Repacker with advanced options")
parser.add_argument("command", choices=["extract", "repack", "extract-all", "repack-all"], help="Command to run")
parser.add_argument("inputs", nargs="*", help="Input files or directories, depends on command")
parser.add_argument("output", nargs="?", help="Output file or directory")
parser.add_argument("--type", nargs='+', choices=[
    "all",
    "Texture2D", "TextAsset", "Mesh",
    "AudioClip", "Shader", "MonoBehaviour", "AnimationClip",
    "Material", "Sprite", "Font", "VideoClip"
], default=["all"], help="Asset types to extract or repack (repack only supports Texture2D, TextAsset, Mesh)")
parser.add_argument("--flat", action="store_true", help="Disable per-type subfolders in output")
parser.add_argument("--dry-run", action="store_true", help="Simulate actions without writing files")
parser.add_argument("--log", type=str, help="Path to write extraction log")
args = parser.parse_args()

# ------------------- Extraction -------------------
def extract_bundle_advanced_filtered(bundle_path: str = None, output_dir: str = None):
    if not bundle_path or not os.path.exists(bundle_path):
        print(f"Error: Invalid bundle path '{bundle_path}'")
        return

    if not output_dir:
        output_dir = Path(bundle_path).stem + "_extracted"
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(bundle_path, "rb") as f:
            env = UnityPy.load(f)
    except Exception as e:
        print(f"Failed to load bundle: {e}")
        return

    type_counter = defaultdict(int)
    log_lines = []

    with tqdm(total=len(env.objects), desc=f"Extracting ({args.type})") as pbar:
        for obj in env.objects:
            obj_type = obj.type.name
            if not should_process_type(obj_type):
                pbar.update(1)
                continue

            try:
                data = obj.read()
                name = get_object_name(data, obj_type, obj.path_id)

                if args.flat:
                    save_dir = output_dir
                    filename_prefix = f"{obj_type}_{name}"
                else:
                    save_dir = os.path.join(output_dir, obj_type)
                    filename_prefix = name

                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename_prefix)

                if obj_type == "Texture2D" and not args.dry_run:
                    data.image.save(save_path + ".png")

                elif obj_type == "TextAsset" and not args.dry_run:
                    content = data.script if isinstance(data.script, str) else data.script.decode("utf-8", errors="surrogateescape")
                    write_text_file(save_path + ".txt", content)

                elif obj_type == "Mesh" and not args.dry_run:
                    write_json_file(save_path + ".json", data.read_typetree())

                elif obj_type == "AudioClip" and getattr(data, "samples", None) and not args.dry_run:
                    write_binary_file(save_path + ".wav", data.samples)

                elif obj_type == "Shader" and not args.dry_run:
                    write_text_file(save_path + ".shader", data.script)

                elif obj_type == "MonoBehaviour" and not args.dry_run:
                    try:
                        write_json_file(save_path + ".json", data.read_typetree())
                    except Exception:
                        write_text_file(save_path + ".txt", str(data))

                elif obj_type == "AnimationClip" and not args.dry_run:
                    write_json_file(save_path + ".json", data.read_typetree())

                elif obj_type == "Material" and not args.dry_run:
                    write_json_file(save_path + ".json", data.read_typetree())

                elif obj_type == "Sprite" and not args.dry_run:
                    try:
                        data.image.save(save_path + ".png")
                    except Exception as e:
                        print(f"Error saving Sprite image: {e}")

                elif obj_type == "Font" and not args.dry_run:
                    try:
                        if hasattr(data, "fontData"):
                            write_binary_file(save_path + ".ttf", data.fontData)
                    except Exception as e:
                        print(f"Error extracting Font: {e}")

                elif obj_type == "VideoClip" and not args.dry_run:
                    try:
                        if hasattr(data, "videoData"):
                            write_binary_file(save_path + ".mp4", data.videoData)
                    except Exception as e:
                        print(f"Error extracting VideoClip: {e}")

                meta = {
                    "type": obj_type,
                    "path_id": obj.path_id,
                    "name": name,
                    "source_bundle": os.path.basename(bundle_path),
                    "original_path": os.path.relpath(save_path, output_dir)
                }
                if not args.dry_run:
                    write_json_file(save_path + ".meta.json", meta)

                type_counter[obj_type] += 1
                log_lines.append(f"{obj_type} -> {save_path}")

            except Exception as e:
                print(f"Error extracting {obj_type}: {e}")
                log_lines.append(f"[ERROR] {obj_type}: {e}")
            pbar.update(1)

    if type_counter:
        print("\nExtracted:")
        for t, count in sorted(type_counter.items()):
            print(f"  {t}: {count}")
    else:
        print("\nNo matching assets extracted.")

    if args.log and not args.dry_run:
        try:
            with open(args.log, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
            print(f"\nLog written to {args.log}")
        except Exception as e:
            print(f"Failed to write log: {e}")

# ------------------- Repacking -------------------
def repack_bundle(input_folder, base_bundle, output_path, asset_type):
    env = UnityPy.Environment()
    env.load_file(base_bundle)
    updated = 0

    for obj in env.objects:
        if "all" not in asset_type and obj.type.name not in asset_type:
            continue
        try:
            data = obj.read()
            name = get_object_name(data, obj.type.name, obj.path_id)
            file_path = os.path.join(input_folder, obj.type.name, name)

            if obj.type.name == "TextAsset" and os.path.exists(file_path + ".txt"):
                data.script = open(file_path + ".txt", "r", encoding="utf-8", errors="surrogateescape").read()
                obj.save(data)
                updated += 1

            elif obj.type.name == "Texture2D" and os.path.exists(file_path + ".png"):
                img = Image.open(file_path + ".png")
                data.set_image(img)
                obj.save(data)
                updated += 1

            elif obj.type.name == "Mesh" and os.path.exists(file_path + ".json"):
                mesh_data = json.load(open(file_path + ".json", "r", encoding="utf-8", errors="surrogateescape"))
                data.save_typetree(mesh_data)
                obj.save(data)
                updated += 1

        except Exception as e:
            print(f"Repack failed for {obj.type.name}: {e}")

    write_binary_file(output_path, env.file.save())
    print(f"Repacked {updated} assets into '{output_path}'")

# ------------------- Entry Point -------------------
def main():
    if args.command == "extract":
        extract_bundle_advanced_filtered(args.inputs[0], args.output)

    elif args.command == "extract-all":
        input_dir = args.inputs[0]
        out_base = args.output or "output"
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.endswith(('.bundle', '.unity3d', '.assets')):
                    extract_bundle_advanced_filtered(os.path.join(root, file), os.path.join(out_base, Path(file).stem))

    elif args.command == "repack":
        repack_bundle(args.inputs[1], args.inputs[0], args.output, args.type)

    elif args.command == "repack-all":
        base_dir = args.inputs[0]
        mod_dir = args.inputs[1]
        out_dir = args.output or "repacked"
        os.makedirs(out_dir, exist_ok=True)

        for file in os.listdir(base_dir):
            if file.endswith(('.bundle', '.unity3d', '.assets')):
                bundle_path = os.path.join(base_dir, file)
                name = Path(file).stem
                extracted_folder = os.path.join(mod_dir, name)
                out_bundle = os.path.join(out_dir, file)

                if os.path.exists(extracted_folder):
                    print(f"Repacking: {file}")
                    repack_bundle(extracted_folder, bundle_path, out_bundle, args.type)
                else:
                    print(f"Warning: No extracted folder found for {file}, skipping")

if __name__ == "__main__":
    main()
