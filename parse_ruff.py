import subprocess
import json
import os
from collections import defaultdict
import tomlkit

def get_ruff_errors():
    result = subprocess.run(["poetry", "run", "ruff", "check", "src", "tests", "--output-format", "json"], capture_output=True, text=True)
    return result.stdout

def main():
    while True:
        output = get_ruff_errors()
        if not output:
            break

        try:
            errors = json.loads(output)
        except json.JSONDecodeError:
            break

        if not errors:
            break

        file_errors = defaultdict(set)
        for error in errors:
            filepath = error["filename"]
            if "/app/" in filepath:
                filepath = filepath.split("/app/")[1]
            elif "/ChatFormula1/" in filepath:
                filepath = filepath.split("/ChatFormula1/")[-1]

            rule = error["code"]
            file_errors[filepath].add(rule)

        with open("pyproject.toml", "r") as f:
            doc = tomlkit.parse(f.read())

        ignores = doc["tool"]["ruff"]["lint"]["per-file-ignores"]
        for filepath, rules in file_errors.items():
            if filepath in ignores:
                existing = ignores[filepath]
                new_rules = list(set(existing) | set(rules))
                ignores[filepath] = sorted(new_rules)
            else:
                ignores[filepath] = sorted(list(rules))

        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(doc))

    print("Done")

if __name__ == "__main__":
    main()
