import csv
import subprocess
import re
import os
from pathlib import Path

def parse_time_range(time_str):
    """Parse time range like '4:15-6:15' into start and end times in seconds."""
    def time_to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return int(parts[0])
    
    start, end = time_str.split('-')
    return time_to_seconds(start.strip()), time_to_seconds(end.strip())

def extract_prefix_from_header(header):
    """Extract prefix from header like 'id (SC),time' -> 'SC'."""
    match = re.search(r'\(([^)]+)\)', header)
    if match:
        return match.group(1)
    return None

def format_time(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def download_youtube_segment(video_id, start_time, end_time, output_path, cookies_file=None):
    """Download YouTube video segment as WAV using yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Calculate duration
    duration = end_time - start_time
    start_time_str = format_time(start_time)
    
    # Create temporary file path for full audio download
    temp_dir = output_path.parent
    temp_path = temp_dir / f"temp_{video_id}.wav"
    
    # Build download methods using the working command format
    download_methods = []
    
    # If cookies file exists, add methods using it first
    if cookies_file and Path(cookies_file).exists():
        download_methods.extend([
            # Method 1: Use cookies file (Chrome)
            [
                'yt-dlp',
                '-i',  # Ignore errors, continue
                '--extract-audio',
                '--audio-format', 'wav',
                '--audio-quality', '0',  # Best quality
                '--ffmpeg-location', '/opt/homebrew/bin',
                '--cookies', str(cookies_file),
                '--output', str(temp_path),
                url
            ],
        ])
    
    # Add browser cookie methods - try different browsers
    for browser in ['chrome', 'safari', 'firefox']:
        download_methods.append([
            'yt-dlp',
            '-i',  # Ignore errors, continue
            '--extract-audio',
            '--audio-format', 'wav',
            '--audio-quality', '0',  # Best quality
            '--ffmpeg-location', '/opt/homebrew/bin',
            '--cookies-from-browser', browser,
            '--output', str(temp_path),
            url
        ])
    
    # Try each method until one works
    last_error = None
    for i, download_cmd in enumerate(download_methods, 1):
        try:
            print(f"  Downloading audio (method {i})...")
            result = subprocess.run(download_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # Save error message but continue to check if file was downloaded
            last_error = e.stderr if e.stderr else e.stdout if e.stdout else str(e)
        
        # Check if file was downloaded (even if command reported error)
        # Since we're downloading directly to WAV, check for the temp file
        if temp_path.exists() and temp_path.stat().st_size > 0:
            print(f"  Downloaded: {temp_path.name} ({temp_path.stat().st_size} bytes)")
            break
        
        # If we didn't find a file and this wasn't the last method, continue
        if i < len(download_methods):
            print(f"  Method {i} failed, trying next method...")
            continue
        else:
            # All methods failed
            print(f"✗ Error downloading {video_id}")
            if last_error:
                print(f"  Error: {last_error}")
            if last_error and ("403" in last_error or "Forbidden" in last_error):
                print(f"  💡 Tip: Try updating yt-dlp: pip install --upgrade yt-dlp")
            if last_error and ("bot" in last_error.lower() or "cookies" in last_error.lower()):
                print(f"  💡 Tip: The script is trying to use browser cookies. Make sure you're logged into YouTube in Chrome/Safari/Firefox.")
            # Clean up any partial downloads
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    # Check if download was successful
    if not temp_path.exists() or temp_path.stat().st_size == 0:
        print(f"✗ Error: Download failed for {video_id}")
        if temp_path.exists():
            temp_path.unlink()
        return False
    
    try:
        # Step 2: Trim audio to segment using ffmpeg
        print(f"  Trimming segment ({start_time_str}, duration: {duration}s)...")
        trim_cmd = [
            '/opt/homebrew/bin/ffmpeg',
            '-i', str(temp_path),
            '-ss', start_time_str,
            '-t', str(duration),
            '-acodec', 'pcm_s16le',  # WAV format, 16-bit PCM
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            '-y',  # Overwrite output file
            str(output_path)
        ]
        subprocess.run(trim_cmd, check=True, capture_output=True)
        
        # Step 3: Remove temporary file
        if temp_path.exists():
            temp_path.unlink()
        
        print(f"✓ Downloaded: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error trimming {video_id}")
        error_msg = e.stderr if e.stderr else e.stdout if e.stdout else "Unknown error"
        print(f"  Error: {error_msg}")
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        return False

def main():
    csv_path = Path('/Users/ndesai-air/Documents/GitHub/ling320/id.csv')
    base_dir = Path('/Users/ndesai-air/Documents/GitHub/ling320')
    wav_dir = base_dir / 'wav'
    wav_dir.mkdir(exist_ok=True)
    
    # Check for cookies - exit with error if not available
    cookies_file = base_dir / 'cookies.txt'
    has_cookies_file = cookies_file.exists()
    
    # Check if browser cookies might be accessible (check common browser paths)
    has_browser_cookies = False
    if not has_cookies_file:
        home = os.path.expanduser("~")
        # Check for Chrome cookies
        chrome_paths = [
            Path(home) / '.config' / 'google-chrome',
            Path(home) / 'Library' / 'Application Support' / 'Google' / 'Chrome',
        ]
        # Check for Safari cookies
        safari_paths = [
            Path(home) / 'Library' / 'Cookies',
        ]
        # Check for Firefox cookies
        firefox_paths = [
            Path(home) / '.mozilla' / 'firefox',
            Path(home) / 'Library' / 'Application Support' / 'Firefox',
        ]
        
        all_browser_paths = chrome_paths + safari_paths + firefox_paths
        for path in all_browser_paths:
            if path.exists():
                has_browser_cookies = True
                break
    
    if not has_cookies_file and not has_browser_cookies:
        print("\n✗ ERROR: Cookies are required but not available!")
        print("  Please provide one of the following:")
        print("  1. A cookies.txt file in the script directory")
        print("     Export cookies using: yt-dlp --cookies-from-browser chrome --cookies cookies.txt")
        print("  2. Be logged into YouTube in Chrome, Safari, or Firefox")
        print("     The script will automatically extract cookies from your browser")
        import sys
        sys.exit(1)
    
    if has_cookies_file:
        print(f"✓ Using cookies file: {cookies_file}")
    else:
        print(f"✓ Using browser cookies")
    
    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        # Initialize variables
        prefix = None
        output_folder = None
        video_id_counts = {}
        
        # Process each row
        for row in reader:
            # Check if this is a header row (contains "id (")
            if len(row) > 0 and 'id (' in row[0].lower():
                # Extract new prefix from header
                prefix = extract_prefix_from_header(row[0])
                if prefix:
                    print(f"\n{'='*60}")
                    print(f"Processing prefix: {prefix}")
                    print(f"{'='*60}")
                    # Create output folder for this prefix
                    output_folder = wav_dir / prefix
                    output_folder.mkdir(exist_ok=True)
                    print(f"Output folder: {output_folder}")
                    # Reset video ID counts for new prefix
                    video_id_counts = {}
                continue
            
            # Skip empty rows or rows without enough data
            if len(row) < 2:
                continue
            
            # Skip if we don't have a valid prefix yet
            if not prefix or not output_folder:
                continue
            
            video_id = row[0].strip()
            time_range = row[1].strip()
            
            if not video_id or not time_range:
                continue
            
            # Validate video ID (YouTube IDs are typically 11 characters)
            if len(video_id) != 11:
                print(f"\n⚠ Skipping {video_id}: Invalid video ID length ({len(video_id)} characters, expected 11)")
                continue
            
            # Parse time range
            start_time, end_time = parse_time_range(time_range)
            
            # Track occurrences and add segment suffix
            if video_id in video_id_counts:
                video_id_counts[video_id] += 1
            else:
                video_id_counts[video_id] = 0
            
            seg_num = video_id_counts[video_id]
            
            # Create output filename with segment suffix
            output_filename = f"{prefix}-{video_id}_seg{seg_num}.wav"
            output_path = output_folder / output_filename
            
            print(f"\nProcessing: {video_id} ({time_range})")
            print(f"  Start: {start_time}s, End: {end_time}s")
            print(f"  Output: {output_path}")
            
            # Check if file already exists
            # if output_path.exists() and output_path.stat().st_size > 0:
            #     print(f"  ✓ File already exists, skipping download")
            #     continue
            
            # Download segment
            cookies_file_path = str(cookies_file) if has_cookies_file else None
            download_youtube_segment(video_id, start_time, end_time, output_path, cookies_file_path)

if __name__ == '__main__':
    main()

