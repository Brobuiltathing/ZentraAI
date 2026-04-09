import importlib.util
import os
import sys
from pathlib import Path

from zentra.logger import log

PLUGINS_FOLDER = os.path.join(os.getcwd(), "plugins")

_loaded_plugins: dict[str, dict] = {}


def load_plugins() -> int:
    Path(PLUGINS_FOLDER).mkdir(parents=True, exist_ok=True)

    readme = Path(PLUGINS_FOLDER) / "README.md"
    if not readme.exists():
        readme.write_text(
            "# ZENTRA Plugins\n\n"
            "Drop Python files here to add custom actions.\n\n"
            "Each plugin must define:\n"
            "  PLUGIN_NAME = 'my_action'\n"
            "  PLUGIN_DESCRIPTION = 'What it does'\n"
            "  def handle(data: dict) -> str:\n"
            "      return 'result'\n\n"
            "The plugin will be available as an action named PLUGIN_NAME.\n"
        )

    count = 0
    for py_file in Path(PLUGINS_FOLDER).glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            name = getattr(module, "PLUGIN_NAME", py_file.stem)
            description = getattr(module, "PLUGIN_DESCRIPTION", "No description")
            handler = getattr(module, "handle", None)

            if handler and callable(handler):
                _loaded_plugins[name] = {
                    "name": name,
                    "description": description,
                    "handler": handler,
                    "file": str(py_file),
                }
                count += 1
                log.info(f"Plugin loaded: {name} ({py_file.name})")
            else:
                log.warning(f"Plugin {py_file.name} has no handle() function, skipped")

        except Exception as exc:
            log.error(f"Failed to load plugin {py_file.name}: {exc}")

    return count


def get_plugin(name: str):
    return _loaded_plugins.get(name)


def get_all_plugins() -> dict:
    return dict(_loaded_plugins)


def handle_plugin_list(data: dict) -> str:
    if not _loaded_plugins:
        return (
            "No plugins loaded.\n"
            f"Drop .py files into `{PLUGINS_FOLDER}` to add custom actions."
        )

    lines = [f"**Plugins** ({len(_loaded_plugins)} loaded)\n"]
    for name, info in _loaded_plugins.items():
        lines.append(f"  **{name}** - {info['description']}")
        lines.append(f"    File: `{info['file']}`")
    return "\n".join(lines)


def handle_plugin_run(data: dict) -> str:
    name = (data.get("app") or "").strip()
    if not name:
        return "plugin_run: provide the plugin name in 'app' field."

    plugin = get_plugin(name)
    if not plugin:
        available = ", ".join(_loaded_plugins.keys()) if _loaded_plugins else "none"
        return f"Plugin '{name}' not found. Available: {available}"

    try:
        result = plugin["handler"](data)
        return result if result else "Plugin returned no output."
    except Exception as exc:
        log.error(f"Plugin '{name}' error: {exc}", exc_info=True)
        return f"Plugin '{name}' failed: {exc}"


def reload_plugins() -> str:
    _loaded_plugins.clear()
    count = load_plugins()
    return f"Reloaded {count} plugin(s)."
