import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

class SpotifyService:
    _instance = None

    def __init__(self):
        self.sp = None
        self._initialized = False

    def _lazy_init(self):
        if self._initialized: return
        
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]) or "your_spotify" in client_id:
            print("Warning: Spotify credentials incomplete or using placeholders.")
            self._initialized = True
            return

        scope = (
            "user-read-playback-state "
            "user-modify-playback-state "
            "playlist-modify-public "
            "playlist-modify-private "
            "user-read-currently-playing "
            "user-read-recently-played"
        )
        
        try:
            # Use disk cache for token persistence
            cache_path = os.path.join(os.path.dirname(__file__), ".spotify_cache")
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                open_browser=True,
                cache_path=cache_path
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            print("Spotify Service initialized (Auto-Auth mode enabled).")
            print("Spotify Service initialized successfully.")
        except Exception as e:
            print(f"Error initializing Spotify Service: {e}")
        
        self._initialized = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # Helper to ensure init before any call
    def _ensure_sp(self):
        self._lazy_init()
        return self.sp is not None

    # --- Playback ---
    def play(self, uri=None, device_id=None, context_uri=None):
        if not self._ensure_sp(): return "Spotify not configured."
        try:
            # Check devices if no device_id provided
            if not device_id:
                devices_data = self.get_devices()
                devices = devices_data.get('devices', []) if isinstance(devices_data, dict) else []
                if not devices:
                    return "NO_ACTIVE_DEVICE"
                
                # Preferred: find an active device
                active_device = next((d for d in devices if d['is_active']), None)
                if not active_device:
                    # If none active, we might need to pick one or just fail
                    # Usually Spotify API needs an active session.
                    return "NO_ACTIVE_DEVICE"
                device_id = active_device['id']

            self.sp.start_playback(device_id=device_id, uris=[uri] if uri else None, context_uri=context_uri)
            return True
        except Exception as e:
            err_msg = str(e)
            print(f"Spotify Play Error: {err_msg}")
            
            if "NO_ACTIVE_DEVICE" in err_msg or "Player command failed: No active device found" in err_msg:
                return "NO_ACTIVE_DEVICE"

            # Try plain resume if no URI provided
            if not uri and not context_uri:
                try:
                    self.sp.start_playback(device_id=device_id)
                    return True
                except: pass
            return err_msg

    def pause(self, device_id=None):
        if not self._ensure_sp(): return None
        try:
            self.sp.pause_playback(device_id=device_id)
            return True
        except Exception as e: return str(e)

    def next_track(self, device_id=None):
        if not self._ensure_sp(): return None
        try:
            self.sp.next_track(device_id=device_id)
            return True
        except Exception as e: return str(e)

    def previous_track(self, device_id=None):
        if not self._ensure_sp(): return None
        try:
            self.sp.previous_track(device_id=device_id)
            return True
        except Exception as e: return str(e)

    def set_volume(self, volume_percent, device_id=None):
        if not self._ensure_sp(): return None
        try:
            self.sp.volume(volume_percent, device_id=device_id)
            return True
        except Exception as e: return str(e)

    def get_current_playback(self):
        if not self._ensure_sp(): return None
        try:
            return self.sp.current_playback()
        except Exception as e: return {"error": str(e)}

    def get_recently_played(self, limit=5):
        if not self._ensure_sp(): return None
        try:
            return self.sp.current_user_recently_played(limit=limit)
        except Exception as e: return {"error": str(e)}

    # --- Search ---
    def search(self, query, type='track', limit=5):
        if not self._ensure_sp(): return None
        try:
            return self.sp.search(q=query, type=type, limit=limit)
        except Exception as e: return {"error": str(e)}

    # --- Devices ---
    def get_devices(self):
        if not self._ensure_sp(): return None
        try:
            return self.sp.devices()
        except Exception as e: return {"error": str(e)}

    def transfer_playback(self, device_id, force_play=True):
        if not self._ensure_sp(): return None
        try:
            self.sp.transfer_playback(device_id=device_id, force_play=force_play)
            return True
        except Exception as e: return str(e)

    # --- Playlists ---
    def get_user_playlists(self, limit=10):
        if not self._ensure_sp(): return None
        try:
            return self.sp.current_user_playlists(limit=limit)
        except Exception as e: return {"error": str(e)}

    def create_playlist(self, name, description="Created by ReflectOS"):
        if not self._ensure_sp(): return None
        try:
            user_id = self.sp.me()['id']
            return self.sp.user_playlist_create(user=user_id, name=name, description=description)
        except Exception as e: return {"error": str(e)}

    def add_to_playlist(self, playlist_id, tracks):
        if not self._ensure_sp(): return None
        try:
            return self.sp.playlist_add_items(playlist_id=playlist_id, items=tracks)
        except Exception as e: return {"error": str(e)}

    def add_to_queue(self, uri, device_id=None):
        """Adds a track to the user's Spotify queue."""
        if not self._ensure_sp(): return None
        try:
            self.sp.add_to_queue(uri=uri, device_id=device_id)
            return True
        except Exception as e: 
            print(f"Spotify Queue Error: {e}")
            return str(e)
