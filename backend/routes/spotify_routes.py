from flask import Blueprint, jsonify
from services.spotify_service import SpotifyService

spotify_bp = Blueprint('spotify', __name__)

@spotify_bp.route('/status', methods=['GET'])
def get_status():
    """Get current Spotify playback status without triggering the AI pipeline."""
    try:
        service = SpotifyService.get_instance()
        playback = service.get_current_playback()

        if not playback or playback.get('error'):
            return jsonify({
                "is_playing": False,
                "track": None,
                "artist": None,
                "image": None,
                "device": None,
                "progress_ms": 0,
                "duration_ms": 0,
            })

        item = playback.get('item', {})
        return jsonify({
            "is_playing": playback.get('is_playing', False),
            "track": item.get('name', 'Unknown'),
            "artist": ', '.join(a['name'] for a in item.get('artists', [])),
            "image": (item.get('album', {}).get('images', [{}])[0].get('url')
                      if item.get('album', {}).get('images') else None),
            "device": playback.get('device', {}).get('name', 'Unknown'),
            "progress_ms": playback.get('progress_ms', 0),
            "duration_ms": item.get('duration_ms', 0),
        })
    except Exception as e:
        print(f"[SPOTIFY] Status endpoint error: {e}")
        return jsonify({"is_playing": False})

@spotify_bp.route('/next', methods=['POST'])
def next_track():
    """Skip to the next track without triggering the AI pipeline."""
    try:
        service = SpotifyService.get_instance()
        res = service.next_track()
        return jsonify({"success": res is True, "action": "next"})
    except Exception as e:
        print(f"[SPOTIFY] Next track error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@spotify_bp.route('/previous', methods=['POST'])
def previous_track():
    """Skip to the previous track without triggering the AI pipeline."""
    try:
        service = SpotifyService.get_instance()
        res = service.previous_track()
        return jsonify({"success": res is True, "action": "previous"})
    except Exception as e:
        print(f"[SPOTIFY] Previous track error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@spotify_bp.route('/pause', methods=['POST'])
def pause_playback():
    """Pause playback without triggering the AI pipeline."""
    try:
        service = SpotifyService.get_instance()
        res = service.pause()
        return jsonify({"success": res is True, "action": "pause"})
    except Exception as e:
        print(f"[SPOTIFY] Pause error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
