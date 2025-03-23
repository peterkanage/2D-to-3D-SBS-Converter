"""
Audio Support Implementation for 2D to 3D SBS Video Converter

This file contains functions and implementation steps to add audio support to the
2D to 3D SBS Video Converter. The existing converter preserves video but ignores
audio tracks. These modifications ensure that the original audio is included in
the final 3D SBS video output.

Implementation Steps:
--------------------
1. Add audio detection functions (check_audio_stream)
2. Add audio extraction function (extract_audio)
3. Add audio combination function (combine_video_audio)
4. Modify process_video_to_3d_sbs to:
   - Extract audio from input file
   - Create video without audio first
   - Combine processed video with original audio

Usage:
------
You can copy-paste these functions into the notebook or import this file.
The key changes are:
1. Use temp_video_path instead of directly writing to output_path in VideoWriter
2. Extract audio before processing, then combine at the end
"""

import os
import subprocess

def check_audio_stream(file_path):
    """Check if the video file has an audio stream"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1',
             file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # If there's output, an audio stream was found
        return bool(result.stdout.strip())
    except Exception as e:
        print(f"Error checking audio stream: {str(e)}")
        return False

def extract_audio(input_path, output_path):
    """Extract audio from a video file using ffmpeg"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Use ffmpeg to extract audio
        cmd = [
            'ffmpeg',
            '-i', input_path,        # Input file
            '-vn',                   # Disable video
            '-acodec', 'copy',       # Copy audio codec without re-encoding
            '-y',                    # Overwrite output file if it exists
            output_path
        ]
        
        print(f"Extracting audio from {input_path} to {output_path}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error extracting audio: {result.stderr}")
            return None
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print("Audio extraction failed - output file is empty or missing")
            return None
        
        print("Audio extracted successfully")
        return output_path
    except Exception as e:
        print(f"Error during audio extraction: {str(e)}")
        return None

def combine_video_audio(video_path, audio_path, output_path):
    """Combine video and audio files using ffmpeg"""
    try:
        # Use ffmpeg to merge video and audio
        cmd = [
            'ffmpeg',
            '-i', video_path,        # Video file
            '-i', audio_path,        # Audio file
            '-c:v', 'copy',          # Copy video without re-encoding
            '-c:a', 'aac',           # Use AAC for audio (better compatibility)
            '-b:a', '192k',          # Audio bitrate
            '-shortest',             # Match the duration of the shorter file
            '-y',                    # Overwrite output file if it exists
            output_path
        ]
        
        print(f"Combining video and audio into {output_path}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error combining video and audio: {result.stderr}")
            return False
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print("Combination failed - output file is empty or missing")
            return False
        
        print("Video and audio combined successfully")
        return True
    except Exception as e:
        print(f"Error during combination: {str(e)}")
        return False

# =======================================
# MODIFICATIONS FOR PROCESS_VIDEO_TO_3D_SBS
# =======================================
"""
Key modifications to the process_video_to_3d_sbs function:

1. After validating the input video, add:
    # Create temporary directory for intermediate files
    temp_dir = "temp_videos"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Base names for temp files
    timestamp = int(time.time())
    temp_base = os.path.join(temp_dir, f"temp_{timestamp}")
    temp_video_path = f"{temp_base}_video.mp4"  # For video without audio
    temp_audio_path = f"{temp_base}_audio.aac"  # For extracted audio
    
    # Track whether we're processing a segment
    is_segment = False
    original_input = input_path
    
    # Extract audio from the source video (original or segment)
    has_audio = check_audio_stream(input_path)
    if has_audio:
        print("Detected audio stream in the video")
        if extract_audio(input_path, temp_audio_path):
            print(f"Audio extracted to {temp_audio_path}")
        else:
            print("Could not extract audio. Output will have no sound.")
            has_audio = False
    else:
        print("No audio stream detected in the video")

2. Change VideoWriter initialization from:
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
    
To:
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (target_width, target_height))

3. Replace the final encoding section with:
    print("Processing complete!")
    
    # Now combine the processed video with the original audio
    if has_audio:
        print("Combining video with original audio...")
        if combine_video_audio(temp_video_path, temp_audio_path, output_path):
            print("Successfully combined video with audio")
        else:
            print("Audio combination failed. Using high quality encoding for video-only output...")
            # Fall back to just processing the video without audio
            if torch.cuda.is_available():
                subprocess.run([
                    'ffmpeg',
                    '-i', temp_video_path,
                    '-c:v', 'h264_nvenc',  # NVIDIA hardware encoding
                    '-preset', 'p2',       # Medium quality/speed
                    '-b:v', '8M',          # Bitrate
                    '-y',                  # Overwrite output if exists
                    output_path
                ], check=True, timeout=600)
            else:
                subprocess.run([
                    'ffmpeg',
                    '-i', temp_video_path,
                    '-c:v', 'libx264',     # CPU encoding
                    '-preset', 'medium',   # Medium quality/speed
                    '-crf', '23',          # Quality level
                    '-y',                  # Overwrite output if exists
                    output_path
                ], check=True, timeout=600)
    else:
        # No audio to add, just convert the video
        print("No audio to add. Finalizing video with high quality encoding...")
        if torch.cuda.is_available():
            subprocess.run([
                'ffmpeg',
                '-i', temp_video_path,
                '-c:v', 'h264_nvenc',  # NVIDIA hardware encoding
                '-preset', 'p2',       # Medium quality/speed
                '-b:v', '8M',          # Bitrate
                '-y',                  # Overwrite output if exists
                output_path
            ], check=True, timeout=600)
        else:
            subprocess.run([
                'ffmpeg',
                '-i', temp_video_path,
                '-c:v', 'libx264',     # CPU encoding
                '-preset', 'medium',   # Medium quality/speed
                '-crf', '23',          # Quality level
                '-y',                  # Overwrite output if exists
                output_path
            ], check=True, timeout=600)
"""

# =======================================
# INTERFACE AUDIO STATUS MODIFICATIONS
# =======================================
"""
To display audio status in the interface, update:

1. The Gradio interface markdown description:
   gr.Markdown("Convert standard 2D videos to stereoscopic 3D SBS format for VR viewing. Output has a 16:9 aspect ratio (1920x1080) with both eye views side by side. **Preserves original audio track** in the output video.")

2. The output video label:
   output_video = gr.Video(label="Converted 3D SBS Video (16:9 aspect ratio with audio)")

3. In the upload_video and download_from_url_handler functions, add audio detection:
   # Check if the video has audio
   has_audio = check_audio_stream(input_video_path)
   audio_info = " with audio" if has_audio else " without audio"

4. Update the status return to include audio info:
   return preview, f"Video loaded successfully{audio_info}: {result['width']}x{result['height']}, {result['fps']:.2f} FPS, {result['frame_count']} frames, {result['size_mb']:.2f}MB, Duration: {video_duration:.2f}s", start_slider, end_slider, enable_segment

5. Update the process_video function's return:
   # Check if the output video has audio
   has_audio = check_audio_stream(output_video_path)
   audio_info = " with audio" if has_audio else " without audio"
   
   segment_info = f" (segment {segment_start:.1f}s-{segment_end:.1f}s)" if use_segment else ""
   return output_video_path, f"Video processed successfully{segment_info}{audio_info}. Saved to {output_video_path} with 16:9 aspect ratio (1920x1080) as requested."
"""