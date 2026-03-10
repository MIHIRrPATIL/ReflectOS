import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticates the user and creates the Calendar service object."""
        try:
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists("token.json"):
                self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            
            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists("credentials.json"):
                        print("[CALENDAR] Error: credentials.json not found in backend directory.")
                        return
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", SCOPES
                    )
                    # We use a fixed port to prevent redirect_uri_mismatch errors
                    self.creds = flow.run_local_server(port=8080)
                    
                # Save the credentials for the next run
            # Use static_discovery=True (default) to use the local bundled discovery doc
            # to prevent google-api-python-client from trying to fetch the discovery document 
            # using httplib2, which is often broken by eventlet monkeypatching in Windows.
            self.service = build("calendar", "v3", credentials=self.creds, static_discovery=True)
            print("[CALENDAR] Successfully authenticated with Google Calendar.")
            
        except Exception as e:
            print(f"[CALENDAR] Authentication failed: {e}")

    def get_upcoming_events(self, max_results=5):
        """Fetches upcoming events from the user's primary calendar."""
        if not self.service:
            print("[CALENDAR] Service not initialized. Cannot fetch events.")
            return []

        try:
            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            print(f"[CALENDAR] Fetching upcoming {max_results} events")
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            
            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                formatted_events.append({
                    "id": event["id"],
                    "summary": event["summary"],
                    "start": start,
                    "link": event.get("htmlLink", "")
                })
                
            return formatted_events
            
        except Exception as e:
            print(f"[CALENDAR] Error fetching events: {e}")
            return []

    def create_event(self, summary, start_time, end_time, description="Created by ReflectOS"):
        """Creates a new event on the user's primary calendar."""
        if not self.service:
            print("[CALENDAR] Service not initialized. Cannot create event.")
            return None

        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Asia/Kolkata',
                },
            }

            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            print(f"[CALENDAR] Event created: {created_event.get('htmlLink')}")
            return created_event
            
        except Exception as e:
            print(f"[CALENDAR] Error creating event: {e}")
            return None
