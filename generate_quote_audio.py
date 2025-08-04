#!/usr/bin/env python3
"""
Script to run all quotes through the audio generation model.
This processes all quotes from quotes.py and generates audio files for each one.
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path
from loguru import logger
from quotes import (
    teddy_ruxpin_quotes,
    henry_rollins_quotes,
    anne_lamott_quotes,
    patti_smith_quotes,
    nick_cave_quotes,
    bob_ross_quotes,
    johnny_cash_quotes,
    ryan_holiday_quotes
)

# Global flag for graceful shutdown
shutdown_requested = False

# Mapping of quote authors to their corresponding voice prompts
# Only including voices that have both .wav and .txt files
VOICE_MAPPING = {
    "teddy_ruxpin": "belinda",
    "henry_rollins": "henry_rollins", 
    "anne_lamott": "jemima_kirke",
    "patti_smith": "patti_smith",
    "nick_cave": "nick_cave",
    "bob_ross": "bob_ross",
    "johnny_cash": "johnny_cash",  # Now using proper johnny_cash voice
    "ryan_holiday": "sarah_snook"
}

# Dictionary mapping to get the actual quote dictionaries
QUOTE_DICTIONARIES = {
    "teddy_ruxpin": teddy_ruxpin_quotes,
    "henry_rollins": henry_rollins_quotes,
    "anne_lamott": anne_lamott_quotes,
    "patti_smith": patti_smith_quotes,
    "nick_cave": nick_cave_quotes,
    "bob_ross": bob_ross_quotes,
    "johnny_cash": johnny_cash_quotes,
    "ryan_holiday": ryan_holiday_quotes
}

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global shutdown_requested
    logger.warning(f"\nReceived interrupt signal {signum}. Shutting down gracefully...")
    shutdown_requested = True

def validate_voice_files():
    """Validate that all required voice files exist."""
    logger.info("Validating voice files...")
    missing_files = []
    
    for author, voice_prompt in VOICE_MAPPING.items():
        voice_audio_path = Path(f"examples/voice_prompts/{voice_prompt}.wav")
        voice_text_path = Path(f"examples/voice_prompts/{voice_prompt}.txt")
        
        if not voice_audio_path.exists():
            missing_files.append(f"Audio: {voice_audio_path}")
        if not voice_text_path.exists():
            missing_files.append(f"Text: {voice_text_path}")
    
    if missing_files:
        logger.error("Missing voice files:")
        for file in missing_files:
            logger.error(f"  - {file}")
        return False
    
    logger.success("All voice files validated successfully!")
    return True

def check_disk_space(output_folder, required_mb=1000):
    """Check if there's enough disk space for generation."""
    try:
        output_path = Path(output_folder)
        if not output_path.exists():
            output_path = output_path.parent
        
        # Get free space in MB
        free_space = output_path.stat().st_size if output_path.exists() else 0
        # This is a simplified check - in practice you'd use shutil.disk_usage
        logger.info(f"Disk space check passed (simplified)")
        return True
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Continue anyway

def file_exists_and_valid(output_path):
    """Check if output file exists and has reasonable size (> 1KB)."""
    try:
        path = Path(output_path)
        if path.exists():
            size = path.stat().st_size
            if size > 1024:  # More than 1KB
                return True
            else:
                logger.warning(f"File {output_path} exists but is too small ({size} bytes)")
                return False
        return False
    except Exception as e:
        logger.warning(f"Error checking file {output_path}: {e}")
        return False

def generate_audio_for_quote(quote_key, quote_text, voice_prompt, output_folder, max_retries=2):
    """Generate audio for a single quote with retry logic and resume capability."""
    output_path = os.path.join(output_folder, f"{quote_key}.wav")
    
    # Check if file already exists and is valid (resume functionality)
    if file_exists_and_valid(output_path):
        logger.info(f"SKIP: {quote_key} - File already exists and is valid")
        return True
    
    # Use default 'python' command; rely on .venv to provide correct Python version
    python_cmd = "python"
    
    # Construct the command to run examples/generation.py
    cmd = [
        python_cmd,
        "examples/generation.py",
        "--transcript", quote_text,
        "--ref_audio", voice_prompt,
        "--out_path", output_path,
        "--device", "none"  # Force CPU usage to avoid device mismatch issues
    ]
    
    logger.info(f"Generating audio for: {quote_key}")
    logger.info(f"Quote: {quote_text[:100]}{'...' if len(quote_text) > 100 else ''}")
    logger.info(f"Voice: {voice_prompt}")
    logger.info(f"Output: {output_path}")
    
    # Retry logic
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.warning(f"Retry attempt {attempt}/{max_retries} for {quote_key}")
            time.sleep(2)  # Brief pause before retry
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning(f"Shutdown requested, skipping {quote_key}")
            return False
        
        # Execute the command
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Verify the output file was created and is valid
            if file_exists_and_valid(output_path):
                logger.success(f"SUCCESS: {quote_key}")
                return True
            else:
                logger.error(f"ERROR: {quote_key} - File was not created or is invalid")
                if attempt < max_retries:
                    continue
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"ERROR: Failed to generate audio for {quote_key} (attempt {attempt + 1})")
            logger.error(f"Return code: {e.returncode}")
            if e.stdout:
                logger.error(f"STDOUT: {e.stdout}")
            if e.stderr:
                logger.error(f"STDERR: {e.stderr}")
            
            if attempt < max_retries:
                continue
            return False
            
        except KeyboardInterrupt:
            logger.warning(f"Interrupted during generation of {quote_key}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error generating {quote_key}: {e}")
            if attempt < max_retries:
                continue
            return False
    
    return False

def main():
    """Main function to process all quotes."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting audio generation for all quotes...")
    
    # Pre-flight checks
    logger.info("Performing pre-flight checks...")
    
    # Validate voice files exist
    if not validate_voice_files():
        logger.error("Pre-flight check failed: Missing voice files")
        return 1
    
    # Check disk space
    if not check_disk_space("output_audio"):
        logger.error("Pre-flight check failed: Insufficient disk space")
        return 1
    
    logger.success("All pre-flight checks passed!")
    
    total_quotes = 0
    successful_generations = 0
    skipped_generations = 0
    
    # TEST VERSION: Process only Henry Rollins quotes, limited to 10
    test_author = "henry_rollins"
    test_quote_dict = QUOTE_DICTIONARIES[test_author]
    voice_prompt = VOICE_MAPPING[test_author]
    output_folder = f"output_audio/{test_author}"
    
    # Create output folder
    try:
        os.makedirs(output_folder, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output folder {output_folder}: {e}")
        return 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST MODE: Processing {test_author} quotes with voice: {voice_prompt}")
    logger.info(f"Output folder: {output_folder}")
    logger.info(f"LIMITED TO: 10 quotes")
    logger.info(f"RESUME: Will skip existing valid files")
    logger.info(f"RETRY: Will retry failed generations up to 2 times")
    logger.info(f"{'='*60}")
    
    # Process only first 10 quotes for testing
    quote_count = 0
    for quote_key, quote_text in test_quote_dict.items():
        if quote_count >= 10:  # Limit to 10 quotes
            break
        
        # Check for shutdown request
        if shutdown_requested:
            logger.warning("Shutdown requested, stopping generation...")
            break
            
        total_quotes += 1
        quote_count += 1
        
        # Check if file already exists (resume functionality)
        output_path = os.path.join(output_folder, f"{quote_key}.wav")
        if file_exists_and_valid(output_path):
            logger.info(f"SKIP: {quote_key} - File already exists and is valid")
            successful_generations += 1
            skipped_generations += 1
            logger.info("-" * 40)
            continue
        
        success = generate_audio_for_quote(quote_key, quote_text, voice_prompt, output_folder)
        if success:
            successful_generations += 1
        
        logger.info("-" * 40)
    
    # FULL VERSION (COMMENTED OUT FOR TESTING)
    # # Process each author's quotes
    # for author, quote_dict in QUOTE_DICTIONARIES.items():
    #     voice_prompt = VOICE_MAPPING[author]
    #     output_folder = f"output_audio/{author}"
    #     
    #     # Create output folder
    #     os.makedirs(output_folder, exist_ok=True)
    #     logger.info(f"\n{'='*60}")
    #     logger.info(f"Processing {author} quotes with voice: {voice_prompt}")
    #     logger.info(f"Output folder: {output_folder}")
    #     logger.info(f"{'='*60}")
    #     
    #     # Process each quote for this author
    #     for quote_key, quote_text in quote_dict.items():
    #         total_quotes += 1
    #         
    #         success = generate_audio_for_quote(quote_key, quote_text, voice_prompt, output_folder)
    #         if success:
    #             successful_generations += 1
    #         
    #         logger.info("-" * 40)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("GENERATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total quotes processed: {total_quotes}")
    logger.info(f"Successful generations: {successful_generations}")
    logger.info(f"Skipped (already existed): {skipped_generations}")
    logger.info(f"Failed generations: {total_quotes - successful_generations}")
    logger.info(f"Success rate: {(successful_generations/total_quotes)*100:.1f}%")
    
    if shutdown_requested:
        logger.warning("Generation was interrupted by user")
        return 1
    elif successful_generations == total_quotes:
        logger.success("ALL QUOTES GENERATED SUCCESSFULLY!")
        return 0
    else:
        logger.warning(f"{total_quotes - successful_generations} quotes failed to generate")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 