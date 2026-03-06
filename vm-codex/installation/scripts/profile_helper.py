#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path


class YamlError(Exception):
    pass


def parse_scalar(raw: str):
    value = raw.strip()
    if value == "":
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_simple_yaml(path: Path):
    data = {}
    current_list = None
    current_map = None

    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if "#" in line:
                line = line.split("#", 1)[0]
            if not line.strip():
                continue

            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()

            if indent == 0:
                current_list = None
                current_map = None
                if ":" not in stripped:
                    raise YamlError(f"{path}:{lineno}: invalid top-level line")
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value == "":
                    data[key] = None
                    current_key = key
                    # infer intended container type based on key name
                    if key in {"tools", "required_binaries", "required_env_vars", "required_fields", "allowed_fields"}:
                        data[key] = []
                        current_list = key
                    elif key in {"tool_versions"}:
                        data[key] = {}
                        current_map = key
                    else:
                        data[key] = ""
                    continue
                data[key] = parse_scalar(value)
                continue

            if indent != 2:
                raise YamlError(f"{path}:{lineno}: only two-space indentation is supported")

            if stripped.startswith("- "):
                if current_list is None:
                    raise YamlError(f"{path}:{lineno}: list item without list key")
                data[current_list].append(parse_scalar(stripped[2:]))
                continue

            if ":" in stripped:
                if current_map is None:
                    raise YamlError(f"{path}:{lineno}: map item without map key")
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = parse_scalar(value)
                data[current_map][key] = value
                continue

            raise YamlError(f"{path}:{lineno}: unsupported yaml syntax")

    return data


def load_schema(path: Path):
    schema = parse_simple_yaml(path)
    missing = [k for k in ("schema_version", "required_fields", "allowed_fields") if k not in schema]
    if missing:
        raise YamlError(f"Schema missing required fields: {', '.join(missing)}")
    if not isinstance(schema["required_fields"], list) or not isinstance(schema["allowed_fields"], list):
        raise YamlError("Schema fields required_fields/allowed_fields must be lists")
    return schema


def validate_profile(profile, schema, profile_path: Path):
    unknown = sorted(set(profile.keys()) - set(schema["allowed_fields"]))
    if unknown:
        raise YamlError(f"{profile_path}: unknown fields: {', '.join(unknown)}")

    missing = [k for k in schema["required_fields"] if k not in profile]
    if missing:
        raise YamlError(f"{profile_path}: missing required fields: {', '.join(missing)}")

    if profile.get("schema_version") != schema.get("schema_version"):
        raise YamlError(
            f"{profile_path}: schema_version={profile.get('schema_version')} does not match {schema.get('schema_version')}"
        )

    if not isinstance(profile.get("tools"), list) or not profile["tools"]:
        raise YamlError(f"{profile_path}: tools must be a non-empty list")

    for key in ("required_binaries", "required_env_vars"):
        value = profile.get(key, [])
        if value in ("", None):
            profile[key] = []
            value = []
        if not isinstance(value, list):
            raise YamlError(f"{profile_path}: {key} must be a list")

    tool_versions = profile.get("tool_versions", {})
    if tool_versions in ("", None):
        profile["tool_versions"] = {}
    elif not isinstance(tool_versions, dict):
        raise YamlError(f"{profile_path}: tool_versions must be a map")


def build_payload(args):
    schema = load_schema(Path(args.schema_file))
    profile = parse_simple_yaml(Path(args.profile_file))
    validate_profile(profile, schema, Path(args.profile_file))

    versions_data = parse_simple_yaml(Path(args.versions_file))
    default_versions = versions_data.get("tool_versions", {})
    if not isinstance(default_versions, dict):
        raise YamlError("versions file: tool_versions must be a map")

    merged_versions = dict(default_versions)
    for key, value in profile.get("tool_versions", {}).items():
        if value is None:
            continue
        merged_versions[key] = value

    payload = {
        "name": profile["name"],
        "description": profile.get("description", ""),
        "os_family": profile["os_family"],
        "os_version_constraints": str(profile["os_version_constraints"]),
        "tools": profile["tools"],
        "required_binaries": profile.get("required_binaries", []),
        "required_env_vars": profile.get("required_env_vars", []),
        "tool_versions": merged_versions,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Validate and resolve VM installation profiles")
    parser.add_argument("--schema-file", required=True)
    parser.add_argument("--profile-file", required=True)
    parser.add_argument("--versions-file", required=True)
    args = parser.parse_args()

    try:
        payload = build_payload(args)
    except (YamlError, FileNotFoundError) as err:
        print(str(err), file=sys.stderr)
        return 1

    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
