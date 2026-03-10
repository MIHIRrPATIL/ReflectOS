import json
from ai.core.state import ReflectState
from services.spotify_service import SpotifyService

def spotify_playback_node(state: ReflectState):
    """Handles core playback: search, play, pause, skip, volume."""
    from services.ai_service import ai_service
    if state.get("interrupted") or ai_service.active_command_id != state.get("request_id"):
        print(f"[SPOTIFY] Playback node skipped due to interrupt (Request: {state.get('request_id')})")
        state["interrupted"] = True
        return state

    print("Spotify: Playback Node Triggered")
    spotify = SpotifyService.get_instance()
    
    # Maintenance
    state["current_node"] = "spotify_playback_node"
    state["execution_path"] = state.get("execution_path", []) + ["spotify_playback_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    # Idempotency Guard: Don't repeat successful actions in refinement loops
    prev_output = state.get("tool_outputs", {}).get("spotify_playback", {})
    if prev_output.get("success") is True and not state.get("critiques"):
        print("[SPOTIFY] Action already successful, skipping re-execution.")
        return state

    user_input = state.get("user_input", "").lower()
    target = state["context"].get("target_object") # e.g. "Bohemian Rhapsody"
    
    output = {"action": "none", "result": "pending"}

    # Logic: Play/Pause/Skip/Queue/Clear
    if state.get("intent") == "CLEAR_SPOTIFY_QUEUE" or "clear" in user_input or "empty" in user_input:
        # Spotify API doesn't have a direct 'clear queue' endpoint.
        # We can simulate it by pausing or potentially skipping if we want to be aggressive.
        # For now, let's treat it as a pause + message.
        res = spotify.pause()
        output = {"action": "clear_queue", "success": res is True, "message": "Stopped playback and effectively cleared session."}

    elif state.get("intent") == "ADD_SPOTIFY_QUEUE" or "queue" in user_input or "add" in user_input:
        track_name = state["context"].get("track_name") or target
        if track_name:
            search_res = spotify.search(track_name, type='track', limit=1)
            tracks = search_res.get('tracks', {}).get('items', []) if isinstance(search_res, dict) else []
            if tracks:
                track = tracks[0]
                res = spotify.add_to_queue(uri=track['uri'])
                output = {"action": "queue_track", "track": track['name'], "artist": track['artists'][0]['name'], "success": res is True}
            else:
                output = {"action": "queue_track", "success": False, "error": f"Track '{track_name}' not found."}
        else:
            output = {"action": "queue_track", "success": False, "error": "No track name provided to queue."}

    elif "pause" in user_input or "stop" in user_input:
        res = spotify.pause()
        output = {"action": "pause", "success": res is True, "error": res if res is not True else None}
    elif "next" in user_input or "skip" in user_input:
        res = spotify.next_track()
        output = {"action": "next", "success": res is True}
    elif "previous" in user_input or "back" in user_input:
        res = spotify.previous_track()
        output = {"action": "previous", "success": res is True}
    elif "play" in user_input or "start" in user_input or "run" in user_input or state.get("intent") == "PLAY_SPOTIFY":
        track_name = state["context"].get("track_name")
        playlist_name = state["context"].get("playlist_name")
        target_name = track_name or playlist_name or target
        
        # Detect playlist intent directly from user input
        # If user says "play my X playlist" or "play playlist X", extract the name
        is_playlist_request = "playlist" in user_input
        if is_playlist_request and not playlist_name:
            # Extract playlist name by removing common filler words
            import re
            cleaned = re.sub(r'\b(play|my|the|a|playlist|please|can you|could you)\b', '', user_input, flags=re.IGNORECASE).strip()
            if cleaned:
                playlist_name = cleaned
                target_name = playlist_name
                print(f"Spotify: Detected playlist request from user input: '{playlist_name}'")
        
        if target_name:
            # 1. If user explicitly asked for a playlist, search playlists FIRST
            if is_playlist_request or (playlist_name and not track_name):
                search_name = playlist_name or target_name
                print(f"Spotify: Focusing on playlist search for: {search_name}")
                user_playlists = spotify.get_user_playlists(limit=50)
                items = user_playlists.get('items', []) if isinstance(user_playlists, dict) else []
                
                # Fuzzy match: find playlist whose name contains the search term (or vice versa)
                match = next((p for p in items if search_name.lower() in p['name'].lower() or p['name'].lower() in search_name.lower()), None)
                
                if match:
                    res = spotify.play(context_uri=match['uri'])
                    output = {"action": "play_playlist", "playlist": match['name'], "success": res is True}
                    print(f"Spotify: Playing user playlist: {match['name']}")
                else:
                    # Fall back to Spotify catalog search
                    search_res = spotify.search(search_name, type='playlist', limit=1)
                    found = search_res.get('playlists', {}).get('items', []) if isinstance(search_res, dict) else []
                    if found:
                        res = spotify.play(context_uri=found[0]['uri'])
                        output = {"action": "play_playlist", "playlist": found[0]['name'], "success": res is True}
                    else:
                        output = {"action": "error", "error": f"Could not find playlist '{search_name}' in your library or Spotify."}
            
            # 2. If track_name is present OR we haven't found a playlist yet
            if output.get("action") == "none" and target_name:
                # Prioritize Track Search
                search_type = 'track' if track_name else 'track,playlist'
                search_res = spotify.search(target_name, type=search_type, limit=5)
                
                if isinstance(search_res, dict) and "error" not in search_res:
                    # Check tracks first!
                    tracks = search_res.get('tracks', {}).get('items', [])
                    if tracks:
                        track = tracks[0]
                        print(f"Spotify: Found matching track: {track['name']} by {track['artists'][0]['name']}")
                        res = spotify.play(uri=track['uri'])
                        output = {"action": "play_track", "track": track['name'], "artist": track['artists'][0]['name'], "success": res is True}
                    
                    # If no tracks and we allowed playlists
                    elif 'playlists' in search_res:
                        playlists = search_res.get('playlists', {}).get('items', [])
                        if playlists:
                            playlist = playlists[0]
                            res = spotify.play(context_uri=playlist['uri'])
                            output = {"action": "play_playlist", "playlist": playlist['name'], "success": res is True}
                
                if output.get("action") == "none":
                     output = {"action": "error", "error": f"Could not find '{target_name}' on Spotify."}
        else:
            # Resume
            res = spotify.play()
            if res == "NO_ACTIVE_DEVICE":
                output = {
                    "action": "need_device", 
                    "success": False,
                    "message": "I found the music, but no active Spotify device is detected. Please open Spotify on your phone or computer and try again."
                }
            elif res is True:
                output = {"action": "resume", "success": True}
            else:
                # If resume failed and it wasn't a device issue, maybe nothing is in queue
                # We should check if we can suggest something or just ask
                output = {"action": "need_target", "message": "Spotify is open but no track is selected. What should I play?"}
            
    # Volume control (simple percentage extraction)
    import re
    vol_match = re.search(r"(\d+)%", user_input)
    if vol_match:
        vol = int(vol_match.group(1))
        res = spotify.set_volume(vol)
        output = {"action": "volume", "level": vol, "success": res is True}

    state["tool_outputs"]["spotify_playback"] = output
    return state

def spotify_device_node(state: ReflectState):
    """Handles device listing and switching."""
    print("Spotify: Device Node Triggered")
    spotify = SpotifyService.get_instance()
    
    # Maintenance
    state["current_node"] = "spotify_device_node"
    state["execution_path"] = state.get("execution_path", []) + ["spotify_device_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    user_input = state.get("user_input", "").lower()
    devices_data = spotify.get_devices()
    devices = devices_data.get('devices', []) if isinstance(devices_data, dict) else []
    
    output = {"action": "list", "devices": devices}

    # If user wants to switch
    # Use 'device' entity if available, otherwise fallback to 'target_device'
    target_device = state["extracted_entities"].get("device") or state["context"].get("target_device")
    
    if state.get("intent") == "SWITCH_SPOTIFY_DEVICE" or "to" in user_input or "switch" in user_input:
        # Match target_device in list
        if target_device:
            match = next((d for d in devices if target_device.lower() in d['name'].lower()), None)
            if match:
                res = spotify.transfer_playback(match['id'])
                output = {"action": "transfer", "to": match['name'], "success": res is True}
            else:
                output = {"action": "transfer", "success": False, "error": f"Device '{target_device}' not found."}
        else:
             output = {"action": "transfer", "success": False, "error": "Please specify which device you want to switch to."}
    
    state["tool_outputs"]["spotify_devices"] = output
    return state

def spotify_playlist_node(state: ReflectState):
    """Handles playlist discovery and creation."""
    print("Spotify: Playlist Node Triggered")
    spotify = SpotifyService.get_instance()
    
    # Maintenance
    state["current_node"] = "spotify_playlist_node"
    state["execution_path"] = state.get("execution_path", []) + ["spotify_playlist_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    user_input = state.get("user_input", "").lower()
    output = {"action": "lookup"}

    if "create" in user_input or "make" in user_input:
        name = state["context"].get("playlist_name", "My Reflect List")
        res = spotify.create_playlist(name)
        output = {"action": "create", "name": name, "success": "id" in res, "data": res}
    elif state.get("intent") == "LIST_PLAYLISTS" or "list" in user_input or ("playlists" in user_input and "play" not in user_input):
        # Just list playlists
        res = spotify.get_user_playlists(limit=20)
        items = res.get('items', []) if isinstance(res, dict) else []
        playlist_list = [{"name": p['name'], "id": p['id']} for p in items]
        output = {
            "action": "list", 
            "count": len(items), 
            "playlists": playlist_list,
            "display_text": ", ".join([p['name'] for p in playlist_list[:10]])
        }
    else:
        output = {"action": "lookup", "message": "I can list your playlists or create a new one. What would you like to do?"}

    state["tool_outputs"]["spotify_playlists"] = output
    return state

def spotify_status_node(state: ReflectState):
    """Retrieves current track info and status."""
    print("Spotify: Status Node Triggered")
    spotify = SpotifyService.get_instance()
    
    # Maintenance
    state["current_node"] = "spotify_status_node"
    state["execution_path"] = state.get("execution_path", []) + ["spotify_status_node"]

    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}

    playback = spotify.get_current_playback()
    if playback and 'item' in playback:
        item = playback['item']
        output = {
            "is_playing": playback['is_playing'],
            "track": item['name'],
            "artist": item['artists'][0]['name'],
            "album": item['album']['name'],
            "image": item['album']['images'][0]['url'] if item['album']['images'] else None,
            "device": playback['device']['name'],
            "progress_ms": playback['progress_ms'],
            "duration_ms": item['duration_ms']
        }
    else:
        # Fallback to recently played
        recent = spotify.get_recently_played(limit=5)
        recent_tracks = []
        if recent and 'items' in recent:
            for r in recent['items']:
                t = r['track']
                recent_tracks.append({
                    "track": t['name'],
                    "artist": t['artists'][0]['name'],
                    "played_at": r['played_at']
                })
        
        output = {
            "is_playing": False, 
            "info": "Nothing is currently playing.",
            "recently_played": recent_tracks
        }

    state["tool_outputs"]["spotify_status"] = output
    return state
