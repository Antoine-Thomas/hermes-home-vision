# Known-good FFmpeg recipes

All commands here were used successfully in the worked session
(caentravelling.mp4, 1280x720@50fps source -> 1080p@60fps, single music track).

## Single-clip cut + replace audio (WORKED - produced valid 264 MB mp4)
ffmpeg -y -ss 2599.083 -i "caentravelling.mp4" -t 154.867 -i "Jean-Paul Dub - Pélerinage ft. Bout and Huck.wav" -map 0:v -map 1:a -c:v libx264 -crf 18 -preset fast -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:a aac -b:a 192k -shortest "clip_final_4K60.mp4"

Key points:
- -ss BEFORE -i = fast seek (skips to the cut, doesn't decode from 0).
- -map 0:v -map 1:a takes video from input 0, audio ONLY from input 1 -> original audio silently dropped, no -an needed.
- -shortest stops at the shorter of video/audio.
- Scale+pad keeps aspect ratio when upscaling 720p->1080p.

## If the music is SHORTER than the video -> loop it
ffmpeg -y -i "video_only.mp4" -f lavfi -i "amovie='Jean-Paul Dub.wav':loop=0" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest "clip_final_4K60.mp4"

## Multi-clip concat (project with several ordered clips)
Write a concat file, then run ffmpeg -f concat -safe 0 -i concat_list.txt -i "music.wav" -map 0:v -map 1:a -c:v libx264 -crf 18 -preset fast -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:a aac -b:a 192k -shortest "clip_final_4K60.mp4"

concat_list.txt example (paths use forward slashes; escape ':'):
file 'C:/Users/searc/Desktop/4k/caentrav/clip1.mp4'
inpoint 12.5
outpoint 48.2
file 'C:/Users/searc/Desktop/4k/caentrav/clip2.mp4'
inpoint 0
outpoint 30.0

## Verify (always)
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "clip_final_4K60.mp4"
# expect 154.867
ffprobe -v error -show_format -show_streams "clip_final_4K60.mp4"
# expect: video h264 + audio aac

## "moov atom not found" -> NOT corruption
This error means FFmpeg was killed before finalizing the MP4 (e.g. a 180s foreground timeout). Delete the file and re-run in background. The command is fine - the encode just needs to finish. In the session, re-running the exact single-clip command above in background produced a valid 264 MB file.
