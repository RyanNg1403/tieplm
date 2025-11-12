#!/usr/bin/env python3
"""
Transcribe videos using local Whisper.
Works with videos in ../videos/ directory.
"""
import argparse
import json
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List
import whisper
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Transcriber:
    """Transcribe video/audio files using local Whisper."""
    
    def __init__(self, model_name: str = "large-v3", device: str = None):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large, large-v3)
            device: Device to run on ('cuda' or 'cpu'). Auto-detected if None.
        """
        self.model_name = model_name
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Loading Whisper model '{model_name}' on {self.device}...")
        self.model = whisper.load_model(model_name, device=self.device)
        logger.info(f"Model loaded successfully!")
    
    def transcribe(self, video_path: str, language: str = None) -> Dict:
        """
        Transcribe video/audio file with timestamps.
        
        Args:
            video_path: Path to video or audio file
            language: Language code (e.g., 'en', 'vi'). Auto-detected if None.
        
        Returns:
            Dict with transcript text and segments with timestamps
        """
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            logger.info(f"Transcribing: {video_path.name}")
            
            # Transcribe with word-level timestamps
            result = self.model.transcribe(
                str(video_path),
                language=language,
                word_timestamps=True,
                verbose=False
            )
            
            # Format segments
            segments = []
            for segment in result['segments']:
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'words': segment.get('words', [])
                })
            
            transcript_data = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': segments,
                'duration': result.get('duration', 0)
            }
            
            logger.info(f"✓ Transcribed {len(segments)} segments ({result['language']})")
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Failed to transcribe {video_path}: {e}")
            raise


def find_video_files(videos_dir: Path) -> list:
    """Find all video files in directory."""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
    videos = []
    
    for ext in video_extensions:
        videos.extend(videos_dir.glob(f'*{ext}'))
    
    return sorted(videos)


def save_transcript(transcript_data: dict, output_path: Path):
    """Save transcript to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)


def transcribe_all_videos(
    videos_dir: str = "../videos",
    output_dir: str = "../transcripts",
    model: str = "large-v3",
    language: str = None
):
    """Transcribe all videos in directory."""
    
    videos_dir = Path(videos_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all videos
    video_files = find_video_files(videos_dir)
    
    if not video_files:
        logger.error(f"No video files found in {videos_dir}")
        return
    
    logger.info(f"Found {len(video_files)} videos to transcribe")
    logger.info(f"Output directory: {output_dir.absolute()}")
    
    # Initialize transcriber
    logger.info(f"\nInitializing Whisper model: {model}")
    transcriber = Transcriber(model_name=model)
    
    # Track results
    successful = []
    failed = []
    
    # Transcribe each video
    with tqdm(total=len(video_files), desc="Transcribing videos") as pbar:
        for video_path in video_files:
            try:
                # Check if already transcribed
                output_file = output_dir / f"{video_path.stem}.json"
                
                if output_file.exists():
                    logger.info(f"⏭️  Skipping (already transcribed): {video_path.name}")
                    successful.append(str(video_path))
                    pbar.update(1)
                    continue
                
                # Transcribe
                logger.info(f"\n{'='*80}")
                logger.info(f"Transcribing: {video_path.name}")
                logger.info(f"{'='*80}")
                
                transcript = transcriber.transcribe(
                    str(video_path),
                    language=language
                )
                
                # Add metadata
                transcript['video_file'] = video_path.name
                transcript['video_path'] = str(video_path)
                
                # Save transcript
                save_transcript(transcript, output_file)
                
                logger.info(f"✓ Saved transcript to: {output_file.name}")
                logger.info(f"  Duration: {transcript['duration']:.1f}s")
                logger.info(f"  Segments: {len(transcript['segments'])}")
                logger.info(f"  Language: {transcript['language']}")
                
                successful.append(str(video_path))
                
            except Exception as e:
                logger.error(f"✗ Failed to transcribe {video_path.name}: {e}")
                failed.append(str(video_path))
            
            pbar.update(1)
    
    # Save summary
    summary = {
        'total': len(video_files),
        'successful': len(successful),
        'failed': len(failed),
        'model': model,
        'successful_files': successful,
        'failed_files': failed
    }
    
    summary_file = output_dir / "transcription_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*80)
    print("TRANSCRIPTION SUMMARY")
    print("="*80)
    print(f"Total videos: {len(video_files)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"\nTranscripts saved to: {output_dir.absolute()}")
    print(f"Summary saved to: {summary_file}")
    
    if failed:
        print("\nFailed videos:")
        for path in failed:
            print(f"  - {Path(path).name}")


def transcribe_single_video(
    video_path: str,
    output_dir: str = "../transcripts",
    model: str = "large-v3",
    language: str = None
):
    """Transcribe a single video."""
    
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return
    
    # Initialize transcriber
    logger.info(f"Initializing Whisper model: {model}")
    transcriber = Transcriber(model_name=model)
    
    # Transcribe
    logger.info(f"Transcribing: {video_path.name}")
    transcript = transcriber.transcribe(str(video_path), language=language)
    
    # Add metadata
    transcript['video_file'] = video_path.name
    transcript['video_path'] = str(video_path)
    
    # Save
    output_file = output_dir / f"{video_path.stem}.json"
    save_transcript(transcript, output_file)
    
    print(f"\n✓ Transcript saved to: {output_file}")
    print(f"  Duration: {transcript['duration']:.1f}s")
    print(f"  Segments: {len(transcript['segments'])}")
    print(f"  Language: {transcript['language']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transcribe videos using local Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe all videos in ../videos/
  python transcribe_videos.py --all
  
  # Transcribe single video
  python transcribe_videos.py --video "../videos/my_video.mp4"
  
  # Use different model (faster but less accurate)
  python transcribe_videos.py --all --model medium
  
  # Specify language (skip auto-detection)
  python transcribe_videos.py --all --language vi
  
  # Custom output directory
  python transcribe_videos.py --all --output ../my_transcripts

Available models (by size/accuracy):
  tiny, base, small, medium, large, large-v3 (default)
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Transcribe all videos in videos directory"
    )
    parser.add_argument(
        "--video",
        help="Transcribe single video file"
    )
    parser.add_argument(
        "--videos-dir",
        default="../videos",
        help="Directory containing videos (default: ../videos)"
    )
    parser.add_argument(
        "--output",
        default="../transcripts",
        help="Output directory for transcripts (default: ../transcripts)"
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large", "large-v3"],
        help="Whisper model to use (default: large-v3)"
    )
    parser.add_argument(
        "--language",
        help="Language code (e.g., 'en', 'vi'). Auto-detected if not specified."
    )
    
    args = parser.parse_args()
    
    if args.all:
        transcribe_all_videos(
            videos_dir=args.videos_dir,
            output_dir=args.output,
            model=args.model,
            language=args.language
        )
    elif args.video:
        transcribe_single_video(
            video_path=args.video,
            output_dir=args.output,
            model=args.model,
            language=args.language
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

