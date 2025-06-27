import cloudinary
import cloudinary.api
import random
import os
import pickle
import requests
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery
import googleapiclient.http

# --- Cloudinary Configuration ---
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# --- YouTube API Configuration ---
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def get_authenticated_service():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                credentials = pickle.load(token)
            print("Credentials loaded from token.pickle")
        except Exception as e:
            print(f"Error loading token: {e}")
            os.remove(TOKEN_FILE)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                print("Credentials refreshed.")
            except Exception as e:
                print(f"Refresh failed: {e}")
                credentials = None

        if not credentials:
            refresh_token_secret = os.environ.get("GOOGLE_REFRESH_TOKEN")
            if not refresh_token_secret:
                raise ValueError("GOOGLE_REFRESH_TOKEN is missing.")

            with open(CLIENT_SECRETS_FILE, 'r') as f:
                client_config = json.load(f)

            web_config = client_config.get("web") or client_config.get("installed")
            if not web_config:
                raise ValueError("Invalid client_secret.json structure.")

            credentials = Credentials(
                token=None,
                refresh_token=refresh_token_secret,
                token_uri=web_config.get("token_uri"),
                client_id=web_config.get("client_id"),
                client_secret=web_config.get("client_secret"),
                scopes=SCOPES
            )

            credentials.refresh(Request())
            print("Initial credentials created and refreshed.")

    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(credentials, token)
    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def upload_video_to_youtube(youtube_service, video_file_path, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "28"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    print(f"Uploading: {title}")
    insert_request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=googleapiclient.http.MediaFileUpload(video_file_path)
    )
    response = insert_request.execute()
    print("Upload complete.")
    print(f"YouTube URL: https://www.youtube.com/watch?v={response.get('id')}")

def main():
    try:
        print("Fetching Cloudinary videos from 'RonaldoFC/'...")
        result = cloudinary.api.resources(
            type='upload',
            resource_type='video',
            prefix='RonaldoFC/',
            max_results=500
        )

        videos = result.get('resources', [])
        if not videos:
            print("No videos found in Cloudinary folder.")
            return

        random_video = random.choice(videos)
        video_url = random_video.get('secure_url')
        video_public_id = random_video.get('public_id')
        print(f"Selected video: {video_public_id}")

        local_video_filename = f"{video_public_id.split('/')[-1]}"
        if not local_video_filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
            local_video_filename += '.mp4'

        print(f"Downloading {local_video_filename}...")
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(local_video_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download complete.")

        base_name = video_public_id.split('/')[-1]
        youtube_title = base_name.replace('_', ' ').replace('-', ' ').title() + " | China Tech & Knowledge"

        youtube_description = (
            f"Welcome to our channel! In this video, we delve into the incredible world of China's technological advancements, "
            f"sharing fascinating facts and insights related to '{youtube_title}'. From AI and quantum computing to sustainable "
            "energy and space exploration, China is at the forefront of global tech. Join us to expand your knowledge!\n\n"
            "If you found this video insightful, please like, share, and subscribe for more content on technology and global facts!\n\n"
            "--- Background Music Credits ---\n"
            "Music: Anno Domini Beats - Schizo [No Copyright Music]\n"
            "Source: https://youtu.be/bGdC0DRCkYw?si=xcWVcZPDpo1HJy-q\n\n"
            "Disclaimer: I do not claim ownership of the original video content. This video is intended for informational and "
            "educational purposes only. Credit for the original video content goes to the respective creators.\n\n"
            "--- Searching Tags --- \n"
            "#ChinaTech #Technology #Innovation #Facts #Knowledge #AI #QuantumComputing #SpaceExploration #ChineseInnovation "
            "#TechNews #FutureTech #GlobalTech #ScienceFacts #EmergingTech #Robotics #BigData #SmartCities #Shenzhen "
            "#TechInsights #EducationalContent"
        )

        youtube_tags = [
            "ChinaTech", "Technology", "Innovation", "Facts", "Knowledge",
            "AI", "QuantumComputing", "ChineseInnovation", "TechNews",
            "FutureTech", "GlobalTech", "ScienceFacts", "EmergingTech",
            "Robotics", "BigData", "SmartCities", "Shenzhen", "TechInsights",
            "EducationalContent", "China"
        ]

        youtube_service = get_authenticated_service()
        upload_video_to_youtube(youtube_service, local_video_filename, youtube_title, youtube_description, youtube_tags)

        os.remove(local_video_filename)
        print(f"Deleted local file: {local_video_filename}")

        try:
            cloudinary.api.delete_resources([video_public_id], resource_type='video')
            print(f"Deleted from Cloudinary: {video_public_id}")
        except Exception as e:
            print(f"Error deleting Cloudinary video: {e}")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
