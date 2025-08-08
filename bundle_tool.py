#!/usr/bin/env python3
import sys
import os
import json
import time
import shutil
import re
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import UnityPy
from PIL import Image

class UnityBundleTool:
    def __init__(self):
        self.mod_log = []
        self._detect_unity_version()
        self._check_dependencies()

    def _detect_unity_version(self):
        """Auto-detect Unity version from common patterns"""
        version_patterns = [
            r"20\d{2}\.\d+",
            r"\d+\.\d+\.\d+",
        ]
        
        if "UNITY_VERSION" in os.environ:
            UnityPy.config.FALLBACK_UNITY_VERSION = os.environ["UNITY_VERSION"]
            return
            
        version_files = [
            "ProjectSettings/ProjectVersion.txt",
            "unity_version.txt",
            "version.txt"
        ]
        
        for vfile in version_files:
            if os.path.exists(vfile):
                try:
                    with open(vfile) as f:
                        content = f.read()
                        for pattern in version_patterns:
                            match = re.search(pattern, content)
                            if match:
                                UnityPy.config.FALLBACK_UNITY_VERSION = match.group()
                                print(f"ℹ Detected Unity version: {match.group()}")
                                return
                except Exception:
                    continue
        
        UnityPy.config.FALLBACK_UNITY_VERSION = '2021.3.36f1'
        print("⚠ Using default Unity version 2021.3.36f1")

    def _check_dependencies(self):
        """Verify required dependencies are installed"""
        missing = []
        try:
            import UnityPy
        except ImportError:
            missing.append("UnityPy (pip install UnityPy)")
        
        try:
            from PIL import Image
        except ImportError:
            missing.append("Pillow (pip install Pillow)")
            
        try:
            import tqdm
        except ImportError:
            missing.append("tqdm (pip install tqdm)")
            
        if missing:
            print("✖ Missing dependencies:")
            for dep in missing:
                print(f"  - {dep}")
            sys.exit(1)

    def unpack(self, bundle_path):
        """Extract assets from a bundle"""
        bundle_path = os.path.abspath(os.path.expanduser(bundle_path))
        if not os.path.isfile(bundle_path):
            print(f"✖ File not found: {bundle_path}")
            return False

        try:
            base_name = os.path.splitext(os.path.basename(bundle_path))[0]
            output_dir = os.path.join(os.path.dirname(bundle_path), f"{base_name}_extracted")
            os.makedirs(output_dir, exist_ok=True)
            
            textures_dir = os.path.join(output_dir, "Textures")
            textassets_dir = os.path.join(output_dir, "TextAssets")
            os.makedirs(textures_dir, exist_ok=True)
            os.makedirs(textassets_dir, exist_ok=True)

            env = UnityPy.load(bundle_path)
            objects = list(env.objects)
            
            with tqdm(objects, desc=f"Extracting {os.path.basename(bundle_path)}", unit="asset") as pbar:
                for obj in pbar:
                    if obj.type.name == "Texture2D":
                        self._extract_texture(obj, textures_dir)
                    elif obj.type.name == "TextAsset":
                        self._extract_text_asset(obj, textassets_dir)

            print(f"✔ Unpacked to {output_dir}")
            return True
        except Exception as e:
            print(f"✖ Failed to unpack {bundle_path}: {str(e)}")
            return False

    def batch_unpack(self, directory):
        """Process all bundles in directory"""
        directory = os.path.abspath(os.path.expanduser(directory))
        if not os.path.isdir(directory):
            print(f"✖ Directory not found: {directory}")
            return False

        bundles = [f for f in os.listdir(directory) if f.endswith('.bundle')]
        if not bundles:
            print(f"✖ No .bundle files found in {directory}")
            return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(tqdm(
                executor.map(self.unpack, [os.path.join(directory, f) for f in bundles]),
                total=len(bundles),
                desc="Unpacking bundles",
                unit="bundle"
            ))
        return any(results)

    def repack(self, input_bundle, modified_folder=None, compress=True):
        """Create new bundle with modifications (original remains untouched)"""
        input_bundle = os.path.abspath(os.path.expanduser(input_bundle))
        if not os.path.isfile(input_bundle):
            print(f"✖ Input file not found: {input_bundle}")
            return False

        try:
            base_name = os.path.splitext(os.path.basename(input_bundle))[0]
            modified_folder = modified_folder or os.path.join(os.path.dirname(input_bundle), f"{base_name}_extracted")
            modified_folder = os.path.abspath(os.path.expanduser(modified_folder))
            
            textures_dir = os.path.join(modified_folder, "Textures")
            textassets_dir = os.path.join(modified_folder, "TextAssets")
            
            env = UnityPy.load(input_bundle)
            changes = []
            
            with tqdm(env.objects, desc=f"Processing {os.path.basename(input_bundle)}", unit="asset") as pbar:
                for obj in pbar:
                    if obj.type.name == "Texture2D" and os.path.exists(textures_dir):
                        if self._replace_texture(obj, textures_dir):
                            changes.append(f"Texture: {obj.read().m_Name}")
                    elif obj.type.name == "TextAsset" and os.path.exists(textassets_dir):
                        if self._replace_text_asset(obj, textassets_dir):
                            changes.append(f"TextAsset: {obj.read().m_Name}")

            if not changes:
                print("ℹ No modifications made")
                return False

            output_path = os.path.join(os.path.dirname(input_bundle), f"modified_{os.path.basename(input_bundle)}")
            with open(output_path, "wb") as f:
                f.write(env.file.save(packer=('lz4' if compress else 'none')))
            
            self._log_modification(input_bundle, output_path, changes)
            print(f"✔ Created new bundle: {output_path}")
            return True
        except Exception as e:
            print(f"✖ Failed to create new bundle: {str(e)}")
            return False

    def batch_repack(self, directory, compress=True):
        """Create new bundles for all modified assets (originals remain untouched)"""
        directory = os.path.abspath(os.path.expanduser(directory))
        if not os.path.isdir(directory):
            print(f"✖ Directory not found: {directory}")
            return False

        bundles = []
        for file in os.listdir(directory):
            if file.endswith('.bundle') and not file.startswith('modified_'):
                base = os.path.splitext(file)[0]
                extracted = os.path.join(directory, f"{base}_extracted")
                if os.path.exists(extracted):
                    bundles.append((
                        os.path.join(directory, file),
                        extracted
                    ))

        if not bundles:
            print("✖ No unmodified bundles with extracted folders found")
            return False

        print(f"Found {len(bundles)} bundles to create modified versions:")
        for orig, _ in bundles:
            print(f"  {os.path.basename(orig)} → modified_{os.path.basename(orig)}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(tqdm(
                executor.map(lambda x: self.repack(x[0], x[1], compress), bundles),
                total=len(bundles),
                desc="Creating new bundles",
                unit="bundle"
            ))

        success_count = sum(results)
        print(f"\n✔ Successfully created {success_count}/{len(bundles)} new bundles")
        return success_count > 0

    def verify_assets(self, bundle_path):
        """Validate asset integrity"""
        bundle_path = os.path.abspath(os.path.expanduser(bundle_path))
        if not os.path.isfile(bundle_path):
            print(f"✖ File not found: {bundle_path}")
            return False

        issues = []
        try:
            env = UnityPy.load(bundle_path)
            
            for obj in tqdm(env.objects, desc="Verifying", unit="asset"):
                if obj.type.name == "Texture2D":
                    data = obj.read()
                    if not data.m_Name:
                        issues.append(f"Unnamed texture (ID: {obj.path_id})")
                    if not data.image:
                        issues.append(f"Empty texture: {data.m_Name or obj.path_id}")
                        
                elif obj.type.name == "TextAsset":
                    data = obj.read()
                    content = getattr(data, "m_Script", getattr(data, "script", None))
                    if not content:
                        issues.append(f"Empty text asset: {data.m_Name or obj.path_id}")

            if issues:
                print("\n".join(["⚠ Issues found:"] + issues))
                return False
            return True
        except Exception as e:
            print(f"✖ Verification failed: {str(e)}")
            return False

    def show_history(self):
        """Display modification history"""
        if not self.mod_log:
            print("ℹ No modification history found")
            return
        
        print("Modification History:")
        for entry in self.mod_log:
            print(f"\n[{entry['timestamp']}]")
            print(f"Original: {entry['original']}")
            print(f"Created: {entry['modified']}")
            print("Changes:")
            for change in entry['changes']:
                print(f"  - {change}")

    def _extract_texture(self, obj, output_dir):
        """Save texture as PNG"""
        data = obj.read()
        name = data.m_Name or f"texture_{obj.path_id}"
        img = data.image
        img.save(os.path.join(output_dir, f"{name}.png"))

    def _extract_text_asset(self, obj, output_dir):
        """Save text asset with proper encoding"""
        data = obj.read()
        name = data.m_Name or f"textasset_{obj.path_id}"
        content = data.m_Script if hasattr(data, "m_Script") else getattr(data, "script", None)
        
        if content is None:
            return

        ext = self._determine_extension(content)
        file_path = os.path.join(output_dir, f"{name}{ext}")
        
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8', errors='surrogateescape')
                with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(content)
            except UnicodeDecodeError:
                with open(file_path, 'wb') as f:
                    f.write(content)
        else:
            with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(content)

    def _replace_texture(self, obj, textures_dir):
        """Replace texture from file"""
        data = obj.read()
        name = data.m_Name or f"texture_{obj.path_id}"
        png_path = os.path.join(textures_dir, f"{name}.png")

        if os.path.exists(png_path):
            try:
                data.image = Image.open(png_path)
                data.save()
                return True
            except Exception as e:
                print(f"✖ Failed to replace {name}: {str(e)}")
        return False

    def _replace_text_asset(self, obj, textassets_dir):
        """Silently replace text asset from file without encoding warnings"""
        data = obj.read()
        name = data.m_Name or f"textasset_{obj.path_id}"
        
        for ext in [".txt", ".json", ".xml", ".bytes"]:
            file_path = os.path.join(textassets_dir, f"{name}{ext}")
            if os.path.exists(file_path):
                try:
                    # Read as binary and assign directly
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    if hasattr(data, "m_Script"):
                        data.m_Script = content
                    elif hasattr(data, "script"):
                        data.script = content
                    else:
                        continue
                    
                    data.save()
                    return True
                    
                except Exception:
                    continue
        return False

    def _determine_extension(self, content):
        """Guess appropriate file extension"""
        if isinstance(content, bytes):
            try:
                decoded = content.decode('utf-8', errors='strict')
                if decoded.startswith(('{', '[')):
                    return ".json"
                elif '<' in decoded and '>' in decoded:
                    return ".xml"
                return ".txt"
            except UnicodeDecodeError:
                return ".bytes"
        else:
            if isinstance(content, str):
                if content.startswith(('{', '[')):
                    return ".json"
                elif '<' in content and '>' in content:
                    return ".xml"
            return ".txt"

    def _log_modification(self, original, modified, changes):
        """Record modification metadata"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "original": os.path.basename(original),
            "modified": os.path.basename(modified),
            "changes": changes
        }
        self.mod_log.append(entry)
        with open("modifications.json", "w") as f:
            json.dump(self.mod_log, f, indent=2)

def show_help():
    print("""Unity Bundle Tool v2.3 - Safe Modding Pipeline

Usage:
  Single File Operations:
    unpack <bundle_file>            Extract single bundle
    repack <bundle_file> [--fast]   Create modified bundle (original preserved)

  Batch Operations:
    batch-unpack <directory>        Extract all bundles in folder
    batch-repack <directory> [--fast]  Create modified bundles for all changes

  Utilities:
    verify <bundle_file>            Validate asset integrity
    history                         Show modification log
    help                            Show this message

Options:
  --fast       Disable compression for faster processing
  --verbose    Show detailed processing info

Safety Features:
  - Original bundles are never modified
  - New bundles created with 'modified_' prefix
  - No backup files created (original preserved)
  - Clear operation logging

Examples:
  # Create modified version of a bundle
  python bundle_tool.py repack character.bundle

  # Process all bundles in a folder
  python bundle_tool.py batch-repack ./assets --fast
""")

def main():
    tool = UnityBundleTool()
    
    if len(sys.argv) < 2 or sys.argv[1].lower() in ('help', '-h', '--help'):
        show_help()
        sys.exit(0)

    command = sys.argv[1].lower()
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    flags = [a for a in sys.argv[2:] if a.startswith('--')]
    compress = "--fast" not in flags
    verbose = "--verbose" in flags

    try:
        if command == "unpack":
            if len(args) < 1:
                raise ValueError("Missing bundle file path")
            tool.unpack(args[0])
            
        elif command == "batch-unpack":
            if len(args) < 1:
                raise ValueError("Missing directory path")
            tool.batch_unpack(args[0])
            
        elif command == "repack":
            if len(args) < 1:
                raise ValueError("Missing bundle file path")
            tool.repack(args[0], compress=compress)
            
        elif command == "batch-repack":
            if len(args) < 1:
                raise ValueError("Missing directory path")
            tool.batch_repack(args[0], compress=compress)
            
        elif command == "verify":
            if len(args) < 1:
                raise ValueError("Missing bundle file path")
            tool.verify_assets(args[0])
            
        elif command == "history":
            tool.show_history()
            
        else:
            print(f"Error: Unknown command '{command}'")
            show_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()