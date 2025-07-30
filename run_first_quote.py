#!/usr/bin/env python3
"""
Script to run the first Henry Rollins quote through the audio generation model.
This extracts the first dictionary entry from quotes.py and uses examples/generation.py.
"""

import subprocess
import sys, os
from loguru import logger
from quotes import henry_rollins_quotes

def main():


    output_folder = "output_audio/henry_rollins"
    os.makedirs(output_folder, exist_ok=True)

    # Get the first item from henry_rollins_quotes dictionary
    first_key = list(henry_rollins_quotes.keys())[0]
    first_quote = henry_rollins_quotes[first_key]
    
    logger.info(f"Processing first quote:")
    logger.info(f"Key: {first_key}")
    logger.info(f"Quote: {first_quote}")
    logger.info("")
    
    # Use default 'python' command; rely on .venv to provide correct Python version
    python_cmd = "python"
    
    # Construct the command to run examples/generation.py
    cmd = [
        python_cmd,  # Use configured Python interpreter
        "examples/generation.py",
        "--transcript", first_quote,
        "--ref_audio", "henry_rollins", 
        "--out_path", f"{first_key}.wav"
    ]
    
    logger.info("Running command:")
    logger.info(" ".join(cmd))
    logger.info("")
    
    # Execute the command
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.success("SUCCESS!")
        logger.info("STDOUT:")
        logger.info(result.stdout)
        if result.stderr:
            logger.warning("STDERR:")
            logger.warning(result.stderr)
    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: Command failed with return code {e.returncode}")
        logger.error("STDOUT:")
        logger.error(e.stdout)
        logger.error("STDERR:")
        logger.error(e.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())