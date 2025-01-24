import logging
import os
import re
import numpy as np
from dotenv import load_dotenv
from pyht import Client
from pyht.client import TTSOptions
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_creator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VideoCreator')

load_dotenv()

class EventParser:
    EVENT_PATTERNS = {
        'laugh': r'\[laugh\]',
        'surprise': r'\[surprise\]',
        'sad': r'\[sad\]',
        'excited': r'\[excited\]',
        'angry': r'\[angry\]',
        'confused': r'\[confused\]'
    }

    @classmethod
    def parse_events(cls, text):
        """Parse events from text, removing event markers"""
        events = []
        
        for event_type, pattern in cls.EVENT_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                events.append((0.5, event_type))
                text = re.sub(pattern, '', text).strip()
        
        return text, events

class AudioGenerator:
    @staticmethod
    def generate_gtts(text, output_file, lang='id'):
        """Generate audio using Google Text-to-Speech"""
        try:
            tts = gTTS(text, lang=lang)
            tts.save(output_file)
            logger.info(f"gTTS Audio generated: {output_file}")
        except Exception as e:
            logger.error(f"gTTS audio generation error: {e}")

    @staticmethod
    def generate_playht(text, output_file, voice_url):
        """Generate audio using Play.ht"""
        try:
            user_id = os.getenv("PLAY_HT_USER_ID")
            api_key = os.getenv("PLAY_HT_API_KEY")
            client = Client(user_id=user_id, api_key=api_key)

            options = TTSOptions(voice=voice_url)
            with open(output_file, "wb") as audio_file:
                for chunk in client.tts(text, options, voice_engine='PlayDialog', protocol='http'):
                    audio_file.write(chunk)
            
            logger.info(f"Play.ht Audio generated: {output_file}")
        except Exception as e:
            logger.error(f"Play.ht audio generation error: {e}")

class SubtitleGenerator:
    @staticmethod
    def create_subtitle_mask(w, h, text, fontsize=48):
        """
        Membuat mask subtitle dengan penanganan teks panjang
        
        Args:
        - w (int): Lebar frame
        - h (int): Tinggi frame
        - text (str): Teks subtitle
        - fontsize (int): Ukuran font
        
        Returns:
        - numpy.ndarray: Mask subtitle
        """
        mask = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mask)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", fontsize)
        except:
            font = ImageFont.load_default()
        
        def wrap_text(text, font, max_width):
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        
        max_subtitle_width = w - 100
        current_fontsize = fontsize
        wrapped_lines = []
        
        while current_fontsize > 20:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", current_fontsize)
            wrapped_lines = wrap_text(text, font, max_subtitle_width)
            
            if len(wrapped_lines) <= 3:
                break
            
            current_fontsize -= 2
        
        wrapped_text = '\n'.join(wrapped_lines)
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (w - text_width) // 2
        y = (h - text_height) // 2
        
        outline_color = (0, 0, 0, 255)
        outline_width = 2
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                draw.multiline_text((x + offset_x, y + offset_y), wrapped_text, 
                                    font=font, fill=outline_color, align='center')
        
        draw.multiline_text((x, y), wrapped_text, 
                            font=font, fill=(255, 255, 255, 255), align='center')
        
        return np.array(mask)

class ImageProcessor:
    @staticmethod
    def scale_image(image_path, target_height=400):
        """
        Scale gambar dengan mempertahankan rasio aspek
        
        Args:
        - image_path (str): Path gambar
        - target_height (int): Tinggi target gambar
        
        Returns:
        - PIL.Image: Gambar yang telah di-scale
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect_ratio = width / height
                new_width = int(target_height * aspect_ratio)
                return img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        except Exception as e:
            logging.error(f"Error scaling image: {e}")
            return None

class DialogClip:
    EVENT_MOVEMENTS = {
        'laugh': {'shake_amount': 15, 'frequency': 20},
        'surprise': {'shake_amount': 20, 'frequency': 30},
        'sad': {'shake_amount': 5, 'frequency': 10},
        'excited': {'shake_amount': 25, 'frequency': 40},
        'angry': {'shake_amount': 30, 'frequency': 50},
        'confused': {'shake_amount': 10, 'frequency': 15}
    }

    def __init__(self, background, char1, char2, text, speaking_char, duration, events=None):
        self.background = background
        self.char1 = char1
        self.char2 = char2
        self.text = text
        self.speaking_char = speaking_char
        self.duration = duration
        self.events = events or []
        self.frame_width = 1920
        self.frame_height = 1080
        
        logger.info(f"DialogClip created: Speaking Char {speaking_char}, Events: {self.events}")
        
    def __call__(self, t):
        frame = self.background.copy()
        
        char_height = 600
        margin = 10
        char1_width = self.char1.size[0]
        char2_width = self.char2.size[0]
        
        char1_x = margin
        char2_x = self.frame_width - char2_width - margin
        
        char_y = self.frame_height - char_height
        
        shake_amount = 5
        offset = int(shake_amount * np.sin(t * 10))
        
        for event_time, event_type in self.events:
            if t >= event_time and t < event_time + 0.5:
                event_params = self.EVENT_MOVEMENTS.get(event_type, {})
                shake_amount = event_params.get('shake_amount', 5)
                frequency = event_params.get('frequency', 10)
                offset = int(shake_amount * np.sin(t * frequency))
                logger.info(f"Event triggered: {event_type} at time {t}")
        
        if self.speaking_char == 1:
            frame.paste(self.char1, (char1_x + offset, char_y), self.char1)
            frame.paste(self.char2, (char2_x, char_y), self.char2)
        else:
            frame.paste(self.char1, (char1_x, char_y), self.char1)
            frame.paste(self.char2, (char2_x + offset, char_y), self.char2)
        
        subtitle = SubtitleGenerator.create_subtitle_mask(self.frame_width, self.frame_height, self.text)
        
        frame_array = np.array(frame)
        alpha_mask = subtitle[:, :, 3] > 0
        frame_array[alpha_mask] = subtitle[alpha_mask][:, :3]
        
        return frame_array
class Character:
    def __init__(self, name, image_path, voice_url, gender):
        """Inisialisasi karakter"""
        self.name = name
        self.image_path = image_path
        self.voice_url = voice_url
        self.gender = gender
        self.scaled_image = None

    def scale_image(self, target_height=600):  # Updated to match ImageProcessor
        """Scale gambar karakter"""
        self.scaled_image = ImageProcessor.scale_image(self.image_path, target_height)
        return self.scaled_image

    def generate_audio(self, text, output_file, lang='en'):
        """Menghasilkan audio untuk karakter"""
        if lang == 'id':
            AudioGenerator.generate_gtts(text, output_file)
        elif lang == 'en':
            AudioGenerator.generate_playht(text, output_file, self.voice_url)
        
        logger.info(f"Audio generated for {self.name} ({self.gender})")
class VideoCreator:
    @classmethod
    def create_conversation_video_oop(cls, background_path, texts, languages, output_path="output.mp4"):
        logger.info("Starting video creation process")
        background = Image.open(background_path).resize((1920, 1080))
    
        host = Character(
            name="Host",
            image_path="karakter/karaktercowok4.png",
            voice_url="s3://voice-cloning-zero-shot/688d0200-7415-42b4-8726-e2f5693aaac8/williamnarrativesaad/manifest.json",
            gender="male"
        )
    
        maya = Character(
            name="Maya",
            image_path="karakter/karaktercewek3.png",
            voice_url="s3://voice-cloning-zero-shot/a59cb96d-bba8-4e24-81f2-e60b888a0275/charlottenarrativesaad/manifest.json",
            gender="female"
        )

        host.scale_image(600)
        maya.scale_image(600)

        # Parse texts and clean events
        processed_texts = []
        all_events = []
        for text in texts:
            cleaned_text, text_events = EventParser.parse_events(text)
            processed_texts.append(cleaned_text)
            all_events.append(text_events)
            logger.info(f"Processed Text: {cleaned_text}, Events: {text_events}")

        # Audio generation with language-specific logic
        audio_files = [f"dialog_{i}.mp3" for i in range(len(texts))]
        for i, (text, output_file, lang, dialog_events) in enumerate(zip(processed_texts, audio_files, languages, all_events)):
            is_host = i % 4 in [0, 1]
            current_character = host if is_host else maya
            
            if lang == 'en':
                AudioGenerator.generate_playht(text, output_file, current_character.voice_url)
            else:  # 'id'
                AudioGenerator.generate_gtts(text, output_file, lang='id')

        # Video clip creation
        clips = []
        for i, (text, audio_file, dialog_events) in enumerate(zip(processed_texts, audio_files, all_events)):
            audio_clip = AudioFileClip(audio_file)
            duration = audio_clip.duration + 0.5
            speaking_char = 1 if i % 4 in [0, 1] else 2
        
            dialog = DialogClip(
                background, 
                host.scaled_image, 
                maya.scaled_image, 
                text, 
                speaking_char, 
                duration, 
                events=dialog_events
            )
            video_clip = VideoClip(dialog, duration=duration)
        
            final_clip = video_clip.set_audio(audio_clip)
            clips.append(final_clip)
    
        final_video = concatenate_videoclips(clips)
    
        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac'
        )
    
        # Cleanup
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                os.remove(audio_file)
        
        logger.info("Video creation completed successfully")

# Main execution

if __name__ == "__main__":
    
    # Daftar teks percakapan dengan emosi dalam bahasa Inggris dulu, lalu bahasa Indonesia
    texts = [
        "Hey everyone! [laugh] Hahaha, welcome back to the podcast! I'm your host Reza, and today we're going to talk about something super fun and interesting: the myths and facts about learning English. It's gonna be a good one, so stay tuned!",
        "Halo semuanya! [laugh] Hahaha, selamat datang kembali di podcast! Saya host Reza, dan hari ini kita akan membahas sesuatu yang sangat menyenangkan dan menarik: mitos dan fakta tentang belajar Bahasa Inggris. Ini bakal seru, jadi tetap dengarkan ya!",
        
        "Hello! [excited] Wohoo, I'm so happy to be here! Can't wait to dive into all these myths and clear things up for you guys. Trust me, you don't want to miss this!",
        "Halo! [excited] Wohoo, saya sangat senang bisa berada di sini! Gak sabar untuk membahas semua mitos ini dan menjelaskannya untuk kalian semua. Percayalah, kalian tidak mau melewatkannya!",
        
        "So, Chloe, let’s start with the first myth that a lot of people believe: 'You have to be fluent in English before you can start speaking.' What do you think about that?",
        "Jadi, Chloe, mari kita mulai dengan mitos pertama yang banyak dipercaya orang: 'Kamu harus fasih berbahasa Inggris sebelum bisa mulai berbicara.' Menurut kamu bagaimana?",
        
        "[laugh] Hahaha, that's such a common myth, Reza! Actually, that’s not true at all. You can totally start speaking English from day one! The key is practicing, even if you make mistakes. It’s part of the learning process.",
        "[laugh] Hahaha, itu mitos yang sangat umum, Reza! Sebenarnya, itu tidak benar sama sekali. Kamu bisa mulai berbicara Bahasa Inggris sejak hari pertama! Kuncinya adalah latihan, meskipun kamu membuat kesalahan. Itu bagian dari proses belajar.",
        
        "Right? It's like, how else would you learn if you don’t try? [surprise] Wow! I remember when I first started, I was terrified to make mistakes. But now I see it's all part of the fun!",
        "Iya kan? Seperti, bagaimana kamu bisa belajar kalau tidak mencobanya? [surprise] Wow! Saya ingat dulu waktu saya mulai, saya takut banget membuat kesalahan. Tapi sekarang saya menyadari itu semua bagian dari keseruan!",
        
        "[laugh] Hahaha, I totally get that! But seriously, mistakes are how we grow. The more you speak, the more you learn. So, don't be afraid to say something wrong!",
        "[laugh] Hahaha, saya benar-benar mengerti! Tapi serius, kesalahan itu adalah cara kita berkembang. Semakin sering kamu berbicara, semakin banyak yang kamu pelajari. Jadi, jangan takut untuk mengatakan sesuatu yang salah!",
        
        "Exactly! And here’s another myth I hear all the time: 'You need to know every single grammar rule to speak English.' What’s your take on that?",
        "Tepat! Dan ini mitos lain yang sering saya dengar: 'Kamu harus tahu setiap aturan grammar untuk berbicara Bahasa Inggris.' Menurut kamu bagaimana?",
        
        "[laugh] Haha, I used to think that too, but no, that’s not necessary at all. Yes, grammar is important, but you don’t need to know every rule to have a conversation. As long as the message is clear, that's what matters.",
        "[laugh] Haha, saya dulu berpikir begitu juga, tapi tidak, itu tidak perlu sama sekali. Ya, grammar itu penting, tapi kamu tidak perlu tahu setiap aturan untuk bisa berbicara. Yang penting adalah pesan yang disampaikan jelas.",
        
        "I completely agree. I used to focus so much on grammar, and it just made me nervous. [sad] :( There were times I’d be like, 'Wait, did I use the right tense?' and forget to actually speak!",
        "Saya sepenuhnya setuju. Dulu saya terlalu fokus pada grammar, dan itu justru membuat saya gugup. [sad] :( Ada kalanya saya berpikir, 'Eh, sudah benar belum tenses-nya?' sampai lupa untuk berbicara!",
        
        "[laugh] Hahaha, I’ve been there too! But honestly, once I started speaking more, I realized that people just want to understand you, not judge your grammar. So, don't stress about it too much!",
        "[laugh] Hahaha, saya juga pernah begitu! Tapi jujur, setelah saya mulai lebih banyak berbicara, saya menyadari bahwa orang hanya ingin memahami kamu, bukan menghakimi grammar kamu. Jadi, jangan terlalu stres dengan itu!",
        
        "That’s true! And what about the myth that you have to live in an English-speaking country to be fluent?",
        "Itu benar! Dan bagaimana dengan mitos yang mengatakan kamu harus tinggal di negara berbahasa Inggris untuk bisa fasih?",
        
        "[surprise] Wow! I know, right? But that's another myth. There are so many ways to immerse yourself in English, even if you’re not in an English-speaking country. Watch movies, listen to podcasts, join online language exchange groups—there are endless resources!",
        "[surprise] Wow! Iya kan? Tapi itu juga mitos. Ada banyak cara untuk membenamkan diri dalam Bahasa Inggris, bahkan kalau kamu tidak tinggal di negara berbahasa Inggris. Nonton film, dengarkan podcast, bergabung dengan grup pertukaran bahasa online—ada banyak sumber daya!",
        
        "Absolutely! I always tell people, ‘You don’t need to move to London to learn English!’ [laugh] Hahaha! But honestly, technology has made it so easy to practice English no matter where you are.",
        "Tentu saja! Saya selalu bilang ke orang-orang, ‘Kamu gak perlu pindah ke London untuk belajar Bahasa Inggris!’ [laugh] Hahaha! Tapi jujur, teknologi sekarang memudahkan kita untuk berlatih Bahasa Inggris di mana saja.",
        
        "[laugh] Exactly! And another thing I want to mention: 'You can’t learn English quickly.' But that’s not true, either. Yes, learning a language takes time, but if you immerse yourself and practice regularly, you'll improve faster than you think.",
        "[laugh] Tepat! Dan satu hal lagi yang ingin saya sebutkan: 'Kamu gak bisa belajar Bahasa Inggris dengan cepat.' Tapi itu juga tidak benar. Ya, belajar bahasa memang butuh waktu, tapi jika kamu membenamkan diri dan berlatih secara teratur, kamu akan berkembang lebih cepat dari yang kamu kira.",
        
        "[surprise] No way! I thought it would take me years to even get close to being fluent, but with consistent practice, I was surprised how much I improved in just a few months.",
        "[surprise] Gak mungkin! Saya pikir butuh bertahun-tahun untuk bisa fasih, tapi dengan latihan yang konsisten, saya terkejut dengan seberapa cepat saya berkembang hanya dalam beberapa bulan.",
        
        "[laugh] Hahaha, that’s so true! It’s all about setting small goals and celebrating your progress. Don’t focus on how long it’s taking, just keep going!",
        "[laugh] Hahaha, itu benar banget! Semua itu soal menetapkan tujuan kecil dan merayakan kemajuanmu. Jangan fokus pada berapa lama waktu yang dibutuhkan, terus aja jalani!",
        
        "Right! Small wins lead to bigger victories. And last but not least, the myth that learning English has to be boring and hard. What do you think about that?",
        "Betul! Kemenangan kecil akan membawa pada kemenangan besar. Dan yang terakhir, mitos bahwa belajar Bahasa Inggris itu harus membosankan dan sulit. Menurut kamu bagaimana?",
        
        "[laugh] Hahaha, that’s hilarious! Learning English can be so much fun if you make it enjoyable. Play games, listen to music, watch your favorite shows in English. It’s all about making learning feel less like a chore.",
        "[laugh] Hahaha, itu lucu banget! Belajar Bahasa Inggris bisa sangat menyenangkan jika kamu membuatnya menyenangkan. Mainkan permainan, dengarkan musik, tonton acara favoritmu dalam Bahasa Inggris. Semua itu soal membuat belajar terasa tidak seperti pekerjaan rumah.",
        
        "Exactly! Learning English should be fun, not stressful. So, if you're enjoying it, you’re doing it right. [excited] Wohoo! English isn’t a mountain you have to climb, it’s more like an adventure you get to enjoy every day!",
        "Tepat! Belajar Bahasa Inggris itu harus menyenangkan, bukan stres. Jadi, jika kamu menikmatinya, itu berarti kamu sudah melakukannya dengan benar. [excited] Wohoo! Bahasa Inggris bukanlah gunung yang harus kamu daki, itu lebih seperti petualangan yang bisa kamu nikmati setiap hari!",
        
        "[laugh] Hahaha, I love that! So, if you’re out there and feeling discouraged, remember: learning English is a journey, and you're already on the right path!",
        "[laugh] Hahaha, saya suka itu! Jadi, jika kamu merasa putus asa, ingatlah: belajar Bahasa Inggris adalah perjalanan, dan kamu sudah berada di jalur yang tepat!",
        
        "Well said, Chloe! And I hope all of you listening at home now feel a little less stressed about learning English and more excited to jump into it! [excited] Woohoo! Alright, that’s all for today’s episode, folks. Thanks for tuning in, and we'll catch you in the next one!",
        "Well said, Chloe! Dan saya harap kalian yang mendengarkan di rumah sekarang merasa sedikit lebih santai tentang belajar Bahasa Inggris dan lebih bersemangat untuk memulainya! [excited] Woohoo! Oke, itu saja untuk episode kali ini, teman-teman. Terima kasih sudah mendengarkan, dan kita akan bertemu lagi di episode berikutnya!"
    ]
    
    # Bahasa yang digunakan dalam setiap teks
    languages = ['en', 'id', 'en', 'id', 'en', 'id', 'en', 'id', 'en', 'id', 'en', 'id', 'en', 'id', 'en', 'id']

    # Membuat video percakapan dengan menggunakan class VideoCreator
    VideoCreator.create_conversation_video_oop(
        "background5.jpg",  # Background gambar yang digunakan
        texts,              # Daftar teks untuk percakapan
        languages,          # Daftar bahasa untuk setiap teks
        "output2.mp4"       # Nama file output video
    )

