# your_project_name/utils/supabase_utils.py

import os
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from supabase import create_client, Client

# --- Configuration Check and Initialization ---
# Read settings variables
SUPABASE_URL = getattr(settings, 'SUPABASE_URL', None)
# Use the Service Role Key for backend uploads for reliability
SUPABASE_KEY = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
SUPABASE_BUCKET_NAME = getattr(settings, 'SUPABASE_BUCKET_NAME', None)

try:
    if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_BUCKET_NAME:
        # 🟢 Now checks for all three required settings
        raise ValueError("Supabase URL, Key, or Bucket Name is not configured in settings.")

    # Initialize the Supabase Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    # This will catch the ValueError and print the descriptive error
    print(f"FATAL ERROR: Supabase Client initialization failed: {e}")
    supabase = None


# ----------------------------------------------------------------------


def upload_file_to_supabase(file_object: UploadedFile, file_path: str) -> str:
    """
    ... (Rest of the function remains the same, using SUPABASE_BUCKET_NAME)
    """
    if not file_object or not supabase:
        return None

    try:
        # Use the configured bucket name from settings
        bucket_name = SUPABASE_BUCKET_NAME

        # 1. Upload the file content
        supabase.storage.from_(bucket_name).upload(
            file=file_object.read(),
            path=file_path,
            file_options={"content-type": file_object.content_type, "cache-control": "3600"}
        )

        # 2. Get the public URL for the file
        public_url_response = supabase.storage.from_(bucket_name).get_public_url(file_path)

        return public_url_response

    except Exception as e:
        print(f"Supabase upload failed for file {file_path}: {e}")
        return None