#!/usr/bin/env python3
"""
YouTube Video Downloader
Downloads videos from chapters_urls.json using yt-dlp
"""

import sys
import json
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Install it with: pip install -r ../../requirements.txt")
    sys.exit(1)


def load_urls_from_json(json_file):
    """Load URLs from chapters_urls.json file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract all URLs from all chapters
        all_urls = []
        for chapter, urls in data.get('chapters', {}).items():
            all_urls.extend(urls)
        
        return all_urls
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file}': {e}")
        sys.exit(1)


def download_videos(url_list, output_path="videos"):
    """
    Download YouTube videos from a list of URLs.
    
    Args:
        url_list (list): List of YouTube video URLs
        output_path (str): Directory to save downloaded videos
    """
    # Create output directory if it doesn't exist
    Path(output_path).mkdir(parents=True, exist_ok=True)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Best quality video + audio
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',  # Output template
        'merge_output_format': 'mp4',  # Merge to mp4
        'quiet': False,  # Show progress
        'no_warnings': False,
        'ignoreerrors': True,  # Continue on download errors
        'socket_timeout': 30,  # Timeout for network operations
        'retries': 3,  # Retry failed downloads
        'fragment_retries': 3,  # Retry failed fragments
        'extractor_retries': 3,  # Retry failed extractions
    }
    
    # Track statistics and URL to filename mapping
    successful = 0
    failed = 0
    failed_urls = []
    url_mapping = {}
    
    print(f"Starting download of {len(url_list)} videos...")
    print(f"Saving to: {Path(output_path).absolute()}\n")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, url in enumerate(url_list, 1):
            try:
                print(f"\n[{idx}/{len(url_list)}] Downloading: {url}")
                print("Extracting video info...", flush=True)
                
                # Extract info first (without downloading) to get metadata
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Failed to extract video info")
                
                title = info.get('title', 'Unknown')
                print(f"Title: {title}", flush=True)
                print("Starting download...", flush=True)
                
                # Now download the video
                ydl.download([url])
                
                # Get the filename
                ext = info.get('ext', 'mp4')
                filename = f"{title}.{ext}"
                url_mapping[url] = filename
                    
                successful += 1
                print(f"✓ Successfully downloaded video {idx}: {filename}", flush=True)
            except KeyboardInterrupt:
                print("\n\nDownload interrupted by user.")
                break
            except Exception as e:
                failed += 1
                failed_urls.append(url)
                url_mapping[url] = None
                print(f"✗ Failed to download video {idx}: {str(e)}", flush=True)
                import traceback
                traceback.print_exc()
    
    # Save URL mapping to JSON file
    mapping_file = Path(output_path) / "url_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(url_mapping, f, indent=2, ensure_ascii=False)
    print(f"\n✓ URL mapping saved to: {mapping_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total videos: {len(url_list)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed_urls:
        print("\nFailed URLs:")
        for url in failed_urls:
            print(f"  - {url}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download YouTube videos")
    parser.add_argument("--all", action="store_true", help="Download all videos")
    parser.add_argument("--urls", nargs="+", help="Specific URLs to download")
    parser.add_argument("--chapters", nargs="+", help="Specific chapters to download (e.g., 'Chương 2' 'Chương 5')")
    args = parser.parse_args()
    
    # Paths relative to pipeline directory
    script_dir = Path(__file__).parent
    json_file = script_dir.parent.parent / "chapters_urls.json"  # Go up to project root
    videos_dir = script_dir.parent / "videos"  # videos/ is in ingestion/
    
    if args.urls:
        # Download specific URLs
        print(f"Downloading {len(args.urls)} specific URLs...")
        download_videos(args.urls, output_path=str(videos_dir))
        
    elif args.chapters:
        # Download specific chapters
        print(f"Loading URLs from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        video_urls = []
        for chapter in args.chapters:
            if chapter in data.get('chapters', {}):
                urls = data['chapters'][chapter]
                video_urls.extend(urls)
                print(f"Found {len(urls)} videos in {chapter}")
            else:
                print(f"Warning: Chapter '{chapter}' not found in config")
        
        if video_urls:
            print(f"\nTotal: {len(video_urls)} videos to download\n")
            download_videos(video_urls, output_path=str(videos_dir))
        else:
            print("No videos to download")
            
    elif args.all:
        # Download all videos
        print(f"Loading URLs from {json_file}...")
        video_urls = load_urls_from_json(json_file)
        print(f"Found {len(video_urls)} video URLs across all chapters\n")
        download_videos(video_urls, output_path=str(videos_dir))
        
    else:
        parser.print_help()
        print("\nExamples:")
        print("  # Download specific URLs")
        print('  python download.py --urls "https://youtu.be/abc" "https://youtu.be/def"')
        print("\n  # Download specific chapters")
        print('  python download.py --chapters "Chương 2" "Chương 5"')
        print("\n  # Download all videos")
        print("  python download.py --all")


if __name__ == "__main__":
    main()

