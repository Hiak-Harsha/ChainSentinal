import os
import sys
import zipfile
from pathlib import Path

def make_zip():
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root.parent
    zip_path = dist_dir / "ChainSentinel.zip"

    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".vite",
        "dist",
        "htmlcov",
        "scratch",
    }
    exclude_extensions = {".pyc", ".pyo", ".pyd", ".wal"}

    print(f"Creating zip from {repo_root} to {zip_path}...")

    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(repo_root):
            # Modify dirs in-place to avoid descending into excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            rel_root = Path(root).relative_to(repo_root)

            for file in files:
                p = Path(root) / file
                if p.suffix in exclude_extensions:
                    continue
                if file.startswith(".env") and file != ".env.example":
                    continue

                arcname = Path("chainsentinel") / rel_root / file
                zf.write(p, arcname=str(arcname).replace("\\", "/"))
                total_files += 1
                total_uncompressed_bytes += p.stat().st_size

    zip_size = zip_path.stat().st_size
    print(f"Success! Packaged {total_files} files ({total_uncompressed_bytes / (1024*1024):.2f} MB uncompressed) into {zip_path.name} ({zip_size / (1024*1024):.2f} MB).")

if __name__ == "__main__":
    make_zip()
