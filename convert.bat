@echo off
echo Converting MP3 to WAV using ffmpeg...
ffmpeg -i demo_conversation.mp3 -ar 16000 -ac 1 -y demo_conversation_converted.wav
echo Done!
