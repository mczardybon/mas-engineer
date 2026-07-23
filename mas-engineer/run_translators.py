#!/usr/bin/env python3
"""
Run 3 translators in parallel, collect JSON results, then run judge.
Each translator outputs JSON to a separate temp file.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

SOURCE_TEXT = "It is no use crying over spilt milk, but we should not have put all our eggs in one basket in the first place."
TARGET_LANG = "German"
SOURCE_LANG = "English"
RECIPE_DIR = "/root/.config/goose/recipes/translator/sub"

translators = ["translator-literal", "translator-literary", "translator-technical"]
results = {}
errors = {}
lock = threading.Lock()

def run_translator(name):
    recipe = os.path.join(RECIPE_DIR, f"{name}.yaml")
    result_file = tempfile.mktemp(suffix=".json", prefix=f"{name}_")
    
    cmd = [
        "goose", "run",
        "--recipe", recipe,
        "--params", f"source_text={SOURCE_TEXT}",
        "--params", f"target_lang={TARGET_LANG}",
        "--params", f"source_lang={SOURCE_LANG}",
        "2>/dev/null",
        "|", "tee", result_file
    ]
    
    try:
        # Use shell to pipe output
        shell_cmd = f'goose run --recipe {recipe} --params "source_text={SOURCE_TEXT}" --params "target_lang={TARGET_LANG}" --params "source_lang={SOURCE_LANG}" 2>/dev/null | tail -5 > {result_file}'
        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Read the result file
        with open(result_file, 'r') as f:
            content = f.read().strip()
        
        # Try to find JSON in the output
        import re
        json_match = re.search(r'\{.*"style".*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            with lock:
                results[name] = data
        else:
            with lock:
                errors[name] = f"No JSON found in output: {content[:500]}"
    except Exception as e:
        with lock:
            errors[name] = str(e)
    finally:
        if os.path.exists(result_file):
            os.unlink(result_file)

# Run in parallel
threads = []
for t in translators:
    thread = threading.Thread(target=run_translator, args=(t,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print(json.dumps({"results": results, "errors": errors}, indent=2))
