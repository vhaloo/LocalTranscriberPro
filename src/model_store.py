"""Download one checkpoint without inference; manage only named model caches."""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

from platformdirs import user_cache_dir

from src.jobs import check_cancelled
from src.model_cache import aligner_path, modern_model_path, prepare_mlx_model, whisper_repository
from src.models import ALIGNER_REPOSITORY, MODEL_BY_ID, MODEL_CATALOG, get_model, mlx_repository
from src.storage import available_bytes, directory_usage, format_bytes


class ModelStore:
    def __init__(self, root, cache_roots=(), *, prefer_mlx=False, omnilingual_root=None):
        self.root = Path(root)
        self.roots = tuple(dict.fromkeys([self.root, *map(Path, cache_roots)]))
        self.prefer_mlx = prefer_mlx
        self.omnilingual_root = Path(omnilingual_root) if omnilingual_root else (
            Path(user_cache_dir("LocalTranscriberPro", "Vhaloo")) / "omnilingual")

    @classmethod
    def from_engine(cls, engine, device="auto"):
        mode = engine.hardware.normalize_device(device)
        return cls(engine.model_cache, engine.cache_roots(),
                   prefer_mlx=engine.hardware.mlx_available and mode in {"auto", "metal"},
                   omnilingual_root=getattr(engine, "omnilingual_cache_root", None))

    def _named_paths(self):
        """Exact catalogue names only; never discover deletion targets by substrings."""
        for spec in MODEL_CATALOG:
            repositories = ([whisper_repository(spec.model_id), mlx_repository(spec.model_id)]
                            if spec.family == "whisper" else [spec.repository] if spec.repository else [])
            for root in self.roots:
                for repository in repositories:
                    yield root / ("models--" + repository.replace("/", "--")), spec.model_id, False
                if spec.family == "whisper":
                    yield root / (spec.model_id + ".pt"), spec.model_id, False
            if spec.family == "whisper":
                yield self.root / "openai" / (spec.model_id + ".pt"), spec.model_id, False
        yield self.omnilingual_root / "1b-v2", "omnilingual-1b-v2", False
        yield self.omnilingual_root / "glotlid", None, True
        for root in self.roots:
            yield root / ("models--" + ALIGNER_REPOSITORY.replace("/", "--")), None, True

    def entries(self, *, measure=False):
        result, seen = [], set()
        for path, model_id, shared in self._named_paths():
            if not path.exists() or path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            usage = directory_usage(resolved) if measure else None
            result.append(dict(name=path.name, path=str(resolved), model_id=model_id, shared=shared,
                               bytes=usage.bytes if usage else None,
                               size=("~" if usage.partial else "") + format_bytes(usage.bytes) if usage else "",
                               partial=usage.partial if usage else False))
        return result

    def model_entries(self, model_id, *, measure=False):
        return [entry for entry in self.entries(measure=measure) if entry["model_id"] == model_id]

    def download(self, model_id, *, cancel_event=None):
        if model_id not in MODEL_BY_ID:
            raise ValueError("Choose an explicit catalogue checkpoint before downloading")
        check_cancelled(cancel_event)
        spec = get_model(model_id)
        destination = self.omnilingual_root if spec.family == "omnilingual" else self.root
        destination.mkdir(parents=True, exist_ok=True)
        free = available_bytes(destination)
        if free is not None and free < spec.download_space_gb * 1024**3:
            raise OSError(f"Keep {spec.download_space_gb:.1f} GB free on the model drive")
        if spec.family == "whisper":
            if self.prefer_mlx:
                folder = prepare_mlx_model(self.root, model_id)
            else:
                from faster_whisper.utils import download_model
                folder = Path(download_model(model_id, cache_dir=str(self.root)))
        elif spec.family in {"qwen", "parakeet"}:
            folder = modern_model_path(self.root, spec)
            check_cancelled(cancel_event)
            if spec.family == "qwen":
                aligner_path(self.root)
        else:
            from src.local_assets import prepare_assets
            from src.omnilingual import METADATA
            folder = prepare_assets(self.omnilingual_root / "1b-v2", METADATA["repository"],
                METADATA["revision"], METADATA["files"], cancel_event=cancel_event)
            lid = METADATA["lid"]
            prepare_assets(self.omnilingual_root / "glotlid", lid["repository"], lid["revision"],
                           lid["files"], cancel_event=cancel_event)
        check_cancelled(cancel_event)
        return str(folder)

    def delete_path(self, path):
        candidate = Path(path).expanduser().absolute()
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            return False
        allowed = {entry["path"] for entry in self.entries()}
        resolved = candidate.resolve()
        if str(resolved) not in allowed or not candidate.exists():
            return False

        def remove_readonly(function, name, error):
            entry = Path(name).absolute()
            if entry != resolved and resolved not in entry.parents:
                raise error
            if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                raise error
            attributes = getattr(entry.lstat(), "st_file_attributes", 0)
            if not isinstance(error, PermissionError) or not attributes & 1:
                raise error
            # Windows cache/sync folders can carry the DOS read-only bit. This
            # changes that bit only, never ACLs or any path outside this model.
            entry.chmod(stat.S_IREAD | stat.S_IWRITE)
            function(name)

        if resolved.is_dir():
            # Hub file symlinks are unlinked by rmtree. Reject directory links
            # and junctions; model deletion must never traverse another tree.
            pending = [resolved]
            while pending:
                for child in pending.pop().iterdir():
                    if getattr(child, "is_junction", lambda: False)():
                        return False
                    if child.is_symlink():
                        continue
                    if child.is_dir():
                        pending.append(child)
            if sys.version_info >= (3, 12):
                shutil.rmtree(resolved, onexc=remove_readonly)
            else:
                shutil.rmtree(resolved, onerror=lambda function, name, error: remove_readonly(function, name, error[1]))
        else:
            try:
                resolved.unlink()
            except PermissionError as error:
                remove_readonly(os.unlink, str(resolved), error)
        return True
