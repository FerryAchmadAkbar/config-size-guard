import fnmatch
from pathlib import Path

class IgnoreRules:

    def __init__(self, ignore_path: Path | str):
        self.rules = self._load_ignore_rules(ignore_path)

    def is_ignored(self, filepath: Path | str) -> bool:
        file_path_obj = Path(filepath)
        file_str = str(file_path_obj).replace('\\', '/')
        for rule in self.rules:
            if fnmatch.fnmatch(file_str, rule):
                return True
            if fnmatch.fnmatch(file_path_obj.name, rule):
                return True
            for parent in file_path_obj.parents:
                parent_str = str(parent).replace('\\', '/')
                if fnmatch.fnmatch(parent_str + '/', rule.rstrip('*')):
                    return True
        return False

    def _load_ignore_rules(self, ignore_file: Path | str) -> list[str]:
        path = Path(ignore_file)
        if not path.exists():
            return []
        rules = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    rules.append(line)
        except OSError:
            pass
        return rules