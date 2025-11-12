#!/usr/bin/env python3
"""
Transcribe specific video files from chapters 8 and 9.
"""
import json
import logging
from pathlib import Path
from tqdm import tqdm
from transcribe_videos import Transcriber, save_transcript

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Specific videos to transcribe
VIDEOS_TO_TRANSCRIBE = [
    "[CS431 - Chương 8] Part 4_1： Hướng dẫn lập trình với kiến trúc mạng RNN và LSTM.mp4",
    "[CS431 - Chương 8] Part 4_2： Hướng dẫn lập trình với kiến trúc mạng RNN và LSTM.mp4",
    "[CS431 - Chương 9] Part 1_1： Giới thiệu bài toán Dịch máy.mp4",
    "[CS431 - Chương 9] Part 1_2： Giới thiệu bài toán Dịch máy.mp4",
    "[CS431 - Chương 9] Part 2_1： Cơ chế Attention trong Sequence-to-Sequence.mp4",
    "[CS431 - Chương 9] Part 2_2： Cơ chế Attention trong Sequence-to-Sequence.mp4",
    "[CS431 - Chương 9] Part 3： Một số biến thể của Attention.mp4",
]


def main():
    """Transcribe specific videos."""
    
    videos_dir = Path("../videos")
    output_dir = Path("../transcripts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model = "large-v3"
    language = "vi"  # Vietnamese
    
    logger.info(f"Videos directory: {videos_dir.absolute()}")
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info(f"Videos to transcribe: {len(VIDEOS_TO_TRANSCRIBE)}")
    
    # Initialize transcriber
    logger.info(f"\nInitializing Whisper model: {model}")
    transcriber = Transcriber(model_name=model)
    
    # Track results
    successful = []
    failed = []
    skipped = []
    
    # Transcribe each video
    with tqdm(total=len(VIDEOS_TO_TRANSCRIBE), desc="Transcribing videos") as pbar:
        for video_name in VIDEOS_TO_TRANSCRIBE:
            video_path = videos_dir / video_name
            
            try:
                # Check if video exists
                if not video_path.exists():
                    logger.warning(f"⚠️  Video not found: {video_name}")
                    failed.append(video_name)
                    pbar.update(1)
                    continue
                
                # Check if already transcribed
                output_file = output_dir / f"{video_path.stem}.json"
                
                if output_file.exists():
                    logger.info(f"⏭️  Skipping (already transcribed): {video_name}")
                    skipped.append(video_name)
                    pbar.update(1)
                    continue
                
                # Transcribe
                logger.info(f"\n{'='*80}")
                logger.info(f"Transcribing: {video_name}")
                logger.info(f"{'='*80}")
                
                transcript = transcriber.transcribe(
                    str(video_path),
                    language=language
                )
                
                # Add metadata
                transcript['video_file'] = video_name
                transcript['video_path'] = str(video_path)
                
                # Save transcript
                save_transcript(transcript, output_file)
                
                logger.info(f"✓ Saved transcript to: {output_file.name}")
                logger.info(f"  Duration: {transcript['duration']:.1f}s")
                logger.info(f"  Segments: {len(transcript['segments'])}")
                logger.info(f"  Language: {transcript['language']}")
                
                successful.append(video_name)
                
            except Exception as e:
                logger.error(f"✗ Failed to transcribe {video_name}: {e}")
                failed.append(video_name)
            
            pbar.update(1)
    
    # Print summary
    print("\n" + "="*80)
    print("TRANSCRIPTION SUMMARY")
    print("="*80)
    print(f"Total videos: {len(VIDEOS_TO_TRANSCRIBE)}")
    print(f"Successful: {len(successful)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print(f"\nTranscripts saved to: {output_dir.absolute()}")
    
    if successful:
        print("\n✓ Successfully transcribed:")
        for name in successful:
            print(f"  - {name}")
    
    if skipped:
        print("\n⏭️  Skipped (already exist):")
        for name in skipped:
            print(f"  - {name}")
    
    if failed:
        print("\n✗ Failed:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()

