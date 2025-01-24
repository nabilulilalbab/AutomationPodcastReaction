---

# Video Creation with Character Dialogue and Reactions

This project generates video content using character dialogue, emotional reactions, and audio synchronization. It parses input texts for specific events (like laughs, surprise, sadness, etc.), generates audio with different voices, and creates video clips featuring animated characters speaking those dialogues with appropriate reactions.

## Features
- **Text Parsing for Emotions**: Detects emotional events (e.g., laughs, surprise) from text and incorporates them into the video.
- **Multiple Audio Sources**: Supports generating audio using both Google Text-to-Speech (gTTS) and Play.ht (for more natural voices).
- **Character Animation**: Animates characters speaking with accompanying reactions (e.g., shaking when laughing or surprised).
- **Subtitles**: Generates subtitles and embeds them into video clips.
- **Customizable Settings**: Supports custom character images and voice URLs.
- **Video Output**: Combines character images, audio, and subtitles into a full video.

## Installation

To get started, clone this repository and install the required dependencies.

```bash
git clone https://github.com/nabilulilalbab/AutomationPodcastReaction.git
cd char-withreaction
pip install -r requirements.txt
```

Make sure you have the following:
- **Python 3.13.**
- **Required packages**: `moviepy`, `Pillow`, `gTTS`, `pyht`, `numpy`, `python-dotenv`

## Setup

1. **Environment Variables**:
   - Create a `.env` file in the project root with the following keys:
     ```
     PLAY_HT_USER_ID=your_playht_user_id
     PLAY_HT_API_KEY=your_playht_api_key
     ```
   - This is required for Play.ht TTS.

2. **Character Images**: Place your character images in the `karakter/` folder. Ensure these images are PNGs with transparent backgrounds for best results.

3. **Fonts**: The project uses `DejaVuSans.ttf` font for subtitles. Ensure the font is available on your system or modify the script to use another available font.

## Usage

### Generating a Video

To generate a video with a conversation between two characters (with reactions and subtitles), use the `create_conversation_video_oop` method.

Example:

```python
from video_creator import VideoCreator

texts = [
    "Hey everyone! [laugh] Hahaha, welcome back to the podcast! I'm your host Reza...",
    "Halo semuanya! [laugh] Hahaha, selamat datang kembali di podcast! Saya host Reza...",
    # Add more text dialogues here
]

languages = ["en", "id", "en", "id", ...]  # Specify language for each dialogue

background_path = "background.jpg"  # Your background image
output_path = "output_video.mp4"   # The output video file path

VideoCreator.create_conversation_video_oop(background_path, texts, languages, output_path)
```

### How It Works:
- **Text Input**: The text for each dialogue is passed as a list. You can include emotional markers like `[laugh]`, `[surprise]`, etc.
- **Languages**: The `languages` list specifies the language for each dialogue (either `'en'` or `'id'`).
- **Audio and Video Creation**: Audio for each character is generated (either using `gTTS` or `Play.ht`), followed by video creation with animated characters speaking their respective dialogues.

### Generated Video

The output video will:
- Feature two characters (host and Maya) in a conversation.
- Display emotional reactions (like shakes during laughter, surprise, etc.).
- Show subtitles at the bottom of the screen.
- Last for the total duration of all dialogues.

### Cleanup

Temporary audio files are removed after the video is created to save disk space.

## File Structure

```
/Belajar/char/withreaction
│
├── karakter/                 # Character image assets
├── .env                      # Environment variables
├── main.py                   # Main script for generating videos
├── video_creator.py          # Video creation logic
├── requirements.txt          # Python dependencies
├── video_creator.log         # Log file for debugging
└── background.jpg            # Example background image (optional)
```

## Logging

The script generates logs to a file `video_creator.log` for tracking errors and important steps during execution.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

This README outlines your project structure and guides users on how to set up and use the video creation script with character dialogue and reactions.
