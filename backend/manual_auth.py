from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def main():
    print("Starting Offline Authentication...")
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
    )
    
    # We use run_console() instead of run_local_server()
    # This bypasses all port locking, Eventlet bugs, and browser local bindings.
    # It gives you a URL to copy/paste, and you paste the resulting code back in the terminal.
    # 
    # Note: Google has officially deprecated OOB (Out of Band) for standard apps, 
    # but for personal desktop/testing purposes with explicit desktop credentials, it can sometimes work.
    # Otherwise, we can use a fixed port (e.g., 8080) and force the user to open it manually.
    
    try:
        # Let's try the local server but let the OS pick the port without Eventlet interference.
        creds = flow.run_local_server(port=0)
        
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
        print("\n\nSUCCESS: token.json saved! You can close this terminal and go back to ReflectOS.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
