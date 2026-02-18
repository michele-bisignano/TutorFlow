import os
from dotenv import load_dotenv
import datetime
from typing import List, Tuple, Dict, Any, Optional
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
from googleapiclient.discovery import build, Resource # type: ignore

load_dotenv()

# Global Constants
CALENDAR_ID: str = os.getenv('CALENDAR_ID', 'primary') 

# For SCOPES, we convert the string from .env back into a list
env_scopes: str = os.getenv('SCOPES', 'https://www.googleapis.com/auth/calendar.readonly')
SCOPES: List[str] = env_scopes.split(',')


def format_event_details(start_raw: str, end_raw: str) -> Tuple[str, str]:
    """
    @brief Parses raw ISO timestamps to calculate duration and formatted time strings.
    
    @param start_raw: str - ISO 8601 start timestamp.
    @param end_raw: str - ISO 8601 end timestamp.
    
    @return Tuple[str, str]: (formatted_time_range, duration_string).
    @exception ValueError: If timestamps are not in valid ISO format.
    """
    start_dt: datetime.datetime = parser.isoparse(start_raw)
    end_dt: datetime.datetime = parser.isoparse(end_raw)
    
    # Calculate duration
    diff: datetime.timedelta = end_dt - start_dt
    seconds: int = int(diff.total_seconds())
    hours: int = seconds // 3600
    minutes: int = (seconds % 3600) // 60
    
    duration_str: str
    if hours > 0 and minutes > 0:
        duration_str = f"{hours}h {minutes}min"
    elif hours > 0:
        duration_str = f"{hours}h"
    else:
        duration_str = f"{minutes}min"
        
    time_range: str = f"from {start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')}"
    
    return time_range, duration_str

def get_calendar_service() -> Resource:
    """
    @brief Initializes and returns an authorized Google Calendar API service.
    
    @details Handles OAuth2 token generation, storage in 'token.json', and refresh logic.
             Expects 'credentials.json' in the parent directory.
             
    @return Resource: An authorized Google API Discovery Resource for 'calendar' v3.
    @exception FileNotFoundError: If the 'credentials.json' file is missing.
    @exception Exception: If authentication fails.
    """
    creds: Optional[Credentials] = None
    token_file: str = 'token.json'
    secrets_file: str = '../credentials.json'

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES) # type: ignore
        
    if not creds or not creds.valid:# type: ignore
        if creds and creds.expired and creds.refresh_token:# type: ignore
            creds.refresh(Request())# type: ignore
        else:
            if not os.path.exists(secrets_file):
                raise FileNotFoundError(f"Missing required file: {secrets_file}")
                
            flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)# type: ignore
            creds = flow.run_local_server(port=0)# type: ignore
            
        with open(token_file, 'w') as token:
            token.write(creds.to_json())# type: ignore

    # Build the service explicitly
    service: Resource = build('calendar', 'v3', credentials=creds)
    return service

def get_today_lessons() -> List[Dict[str, Any]]:
    """
    @brief Retrieves tutoring sessions ('Ripetizioni') scheduled for the current day.
    
    @details Filters events from 00:00:00 to 23:59:59 of the current date in UTC.
             
    @return List[Dict[str, Any]]: A list of event dictionaries from the Google Calendar API.
    @exception Exception: For API communication or execution errors.
    """
    try:
        service: Resource = get_calendar_service()
        
        # Define the temporal boundaries for 'Today'
        now_dt: datetime.datetime = datetime.datetime.now()
        start_of_day: str = now_dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        end_of_day: str = now_dt.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'
        
        print(f"🔍 Fetching lessons for: {now_dt.strftime('%Y-%m-%d')}...")
        
        # Execute API request
        events_result: Dict[str, Any] = service.events().list(# type: ignore
            calendarId=CALENDAR_ID, 
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime',
            q='Ripetizioni'
        ).execute()# type: ignore
        
        events: List[Dict[str, Any]] = events_result.get('items', [])# type: ignore

        if not events:
            print("No lessons found for today.")
        else:
            print(f"✅ Found {len(events)} lessons:\n" + "-"*40)# type: ignore
            for event in events:# type: ignore
                # Extracting specific fields with type safety
                start_info: Dict[str, str] = event.get('start', {})# type: ignore
                end_info: Dict[str, str] = event.get('end', {})# type: ignore
                
                start_raw: str = start_info.get('dateTime', start_info.get('date', ''))# type: ignore
                end_raw: str = end_info.get('dateTime', end_info.get('date', ''))# type: ignore
                
                summary: str = event.get('summary', 'Untitled')# type: ignore
                description: str = event.get('description', 'No description')# type: ignore

                if start_raw and end_raw:
                    time_info, duration = format_event_details(start_raw, end_raw)# type: ignore
                    print(f"⏰ Time:     {time_info}")
                    print(f"⏳ Duration: {duration}")
                    print(f"👤 Student:  {summary}")
                    print(f"📝 Notes:    {description}")
                    print("-" * 40)
                
        return events# type: ignore
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []

if __name__ == '__main__':
    # Execute script
    lessons: List[Dict[str, Any]] = get_today_lessons()