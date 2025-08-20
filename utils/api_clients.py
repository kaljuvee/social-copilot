import requests
import json
import time
import os
from typing import Dict, List, Tuple, Optional
from utils.database import get_api_credentials, add_to_queue
import streamlit as st

# Character limits for each platform
PLATFORM_CHAR_LIMITS = {
    "Facebook": 63206,
    "Threads": 500,
    "X (Twitter)": 280,
    "LinkedIn": 3000,
    "BlueSky": 300,
    "Mastodon": 500
}

def get_platform_char_limits() -> Dict[str, int]:
    """Return character limits for all platforms"""
    return PLATFORM_CHAR_LIMITS

class APIClient:
    """Base class for API clients"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.credentials = self._load_credentials()
    
    def _env_credentials_for_platform(self) -> Dict[str, str]:
        """Load credentials for this platform from environment variables.
        These act as defaults and may be overridden by values in the DB.
        """
        platform_env_map: Dict[str, Dict[str, str]] = {
            "Facebook": {
                "app_id": "FACEBOOK_APP_ID",
                "app_secret": "FACEBOOK_APP_SECRET",
                "access_token": "FACEBOOK_ACCESS_TOKEN",
            },
            "Threads": {
                "app_id": "THREADS_APP_ID",
                "app_secret": "THREADS_APP_SECRET",
                "access_token": "THREADS_ACCESS_TOKEN",
            },
            "X (Twitter)": {
                "api_key": "TWITTER_API_KEY",
                "api_secret": "TWITTER_API_SECRET",
                "access_token": "TWITTER_ACCESS_TOKEN",
                "access_token_secret": "TWITTER_ACCESS_TOKEN_SECRET",
                "bearer_token": "TWITTER_BEARER_TOKEN",
            },
            "LinkedIn": {
                "client_id": "LINKEDIN_CLIENT_ID",
                "client_secret": "LINKEDIN_CLIENT_SECRET",
                "access_token": "LINKEDIN_ACCESS_TOKEN",
                "person_urn": "LINKEDIN_PERSON_URN",
            },
            "BlueSky": {
                "username": "BLUESKY_USERNAME",
                "password": "BLUESKY_PASSWORD",
            },
            "Mastodon": {
                "instance_url": "MASTODON_INSTANCE_URL",
                "access_token": "MASTODON_ACCESS_TOKEN",
            },
        }
        env_mapping = platform_env_map.get(self.platform, {})
        env_creds: Dict[str, str] = {}
        for key, env_name in env_mapping.items():
            value = os.getenv(env_name)
            if value:
                env_creds[key] = value
        return env_creds

    def _load_credentials(self) -> Optional[Dict]:
        """Load credentials with precedence: env defaults, overridden by DB settings"""
        # Start with environment-provided defaults
        combined_creds: Dict[str, str] = self._env_credentials_for_platform()

        # Merge any DB-provided overrides on top
        creds_json = get_api_credentials(self.platform)
        if creds_json:
            try:
                db_creds = json.loads(creds_json)
                if isinstance(db_creds, dict):
                    combined_creds.update({k: v for k, v in db_creds.items() if v is not None and v != ""})
            except json.JSONDecodeError:
                pass

        return combined_creds if combined_creds else None
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        """Post content to platform - to be implemented by subclasses"""
        raise NotImplementedError

class FacebookClient(APIClient):
    """Facebook Graph API client"""
    
    def __init__(self):
        super().__init__("Facebook")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No Facebook credentials configured"
        
        try:
            # Facebook Graph API endpoint
            url = f"https://graph.facebook.com/v18.0/me/feed"
            
            data = {
                'message': content,
                'access_token': self.credentials.get('access_token')
            }
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Facebook API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Facebook connection error: {str(e)}"
        except Exception as e:
            return False, f"Facebook unexpected error: {str(e)}"

class ThreadsClient(APIClient):
    """Meta Threads API client"""
    
    def __init__(self):
        super().__init__("Threads")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No Threads credentials configured"
        
        try:
            # Threads API is still in development, using placeholder
            # This would need to be updated when Threads API is fully available
            return False, "Threads API not yet fully available"
            
        except Exception as e:
            return False, f"Threads error: {str(e)}"

class TwitterClient(APIClient):
    """X (Twitter) API v2 client"""
    
    def __init__(self):
        super().__init__("X (Twitter)")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No Twitter credentials configured"
        
        try:
            # Twitter API v2 endpoint
            url = "https://api.twitter.com/2/tweets"
            
            headers = {
                'Authorization': f"Bearer {self.credentials.get('bearer_token')}",
                'Content-Type': 'application/json'
            }
            
            data = {
                'text': content
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 201:
                return True, None
            else:
                return False, f"Twitter API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Twitter connection error: {str(e)}"
        except Exception as e:
            return False, f"Twitter unexpected error: {str(e)}"

class LinkedInClient(APIClient):
    """LinkedIn API client"""
    
    def __init__(self):
        super().__init__("LinkedIn")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No LinkedIn credentials configured"
        
        try:
            # LinkedIn API endpoint for sharing
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            headers = {
                'Authorization': f"Bearer {self.credentials.get('access_token')}",
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            # Get person URN (would need to be retrieved from profile)
            person_urn = self.credentials.get('person_urn', 'urn:li:person:YOUR_PERSON_ID')
            
            data = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 201:
                return True, None
            else:
                return False, f"LinkedIn API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return False, f"LinkedIn connection error: {str(e)}"
        except Exception as e:
            return False, f"LinkedIn unexpected error: {str(e)}"

class BlueSkyClient(APIClient):
    """BlueSky AT Protocol client"""
    
    def __init__(self):
        super().__init__("BlueSky")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No BlueSky credentials configured"
        
        try:
            # BlueSky AT Protocol endpoint
            # First, create a session
            session_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
            
            session_data = {
                'identifier': self.credentials.get('username'),
                'password': self.credentials.get('password')
            }
            
            session_response = requests.post(session_url, json=session_data, timeout=30)
            
            if session_response.status_code != 200:
                return False, f"BlueSky auth error: {session_response.status_code}"
            
            session_info = session_response.json()
            access_token = session_info.get('accessJwt')
            
            # Now post
            post_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
            
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
            
            post_data = {
                "repo": session_info.get('did'),
                "collection": "app.bsky.feed.post",
                "record": {
                    "text": content,
                    "createdAt": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
                }
            }
            
            response = requests.post(post_url, headers=headers, json=post_data, timeout=30)
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"BlueSky post error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return False, f"BlueSky connection error: {str(e)}"
        except Exception as e:
            return False, f"BlueSky unexpected error: {str(e)}"

class MastodonClient(APIClient):
    """Mastodon API client"""
    
    def __init__(self):
        super().__init__("Mastodon")
    
    def post(self, content: str) -> Tuple[bool, Optional[str]]:
        if not self.credentials:
            return False, "No Mastodon credentials configured"
        
        try:
            # Mastodon API endpoint
            instance_url = self.credentials.get('instance_url', 'https://mastodon.social')
            url = f"{instance_url}/api/v1/statuses"
            
            headers = {
                'Authorization': f"Bearer {self.credentials.get('access_token')}",
                'Content-Type': 'application/json'
            }
            
            data = {
                'status': content,
                'visibility': 'public'
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Mastodon API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Mastodon connection error: {str(e)}"
        except Exception as e:
            return False, f"Mastodon unexpected error: {str(e)}"

# Platform client mapping
PLATFORM_CLIENTS = {
    "Facebook": FacebookClient,
    "Threads": ThreadsClient,
    "X (Twitter)": TwitterClient,
    "LinkedIn": LinkedInClient,
    "BlueSky": BlueSkyClient,
    "Mastodon": MastodonClient
}

def post_to_platforms(content: str, platforms: List[str]) -> Tuple[bool, Dict[str, str]]:
    """
    Post content to multiple platforms
    Returns: (all_successful, errors_dict)
    """
    results = {}
    errors = {}
    
    for platform in platforms:
        if platform in PLATFORM_CLIENTS:
            try:
                client_class = PLATFORM_CLIENTS[platform]
                client = client_class()
                
                success, error = client.post(content)
                results[platform] = success
                
                if not success and error:
                    errors[platform] = error
                
                # Small delay between posts to avoid rate limits
                time.sleep(1)
                
            except Exception as e:
                results[platform] = False
                errors[platform] = f"Unexpected error: {str(e)}"
        else:
            results[platform] = False
            errors[platform] = f"Platform '{platform}' not supported"
    
    all_successful = all(results.values())
    
    return all_successful, errors

def post_to_single_platform(content: str, platform: str) -> Tuple[bool, Optional[str]]:
    """Post content to a single platform"""
    if platform not in PLATFORM_CLIENTS:
        return False, f"Platform '{platform}' not supported"
    
    try:
        client_class = PLATFORM_CLIENTS[platform]
        client = client_class()
        return client.post(content)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def validate_content_length(content: str, platforms: List[str]) -> Dict[str, bool]:
    """Validate content length for each platform"""
    validation_results = {}
    
    for platform in platforms:
        limit = PLATFORM_CHAR_LIMITS.get(platform, 280)
        validation_results[platform] = len(content) <= limit
    
    return validation_results

def get_rate_limit_delay(platform: str) -> int:
    """Get recommended delay between posts for a platform (in seconds)"""
    delays = {
        "Facebook": 30,    # Facebook has strict rate limits
        "Threads": 10,     # Conservative estimate
        "X (Twitter)": 5,  # Twitter has good rate limits
        "LinkedIn": 60,    # LinkedIn is more restrictive
        "BlueSky": 5,      # AT Protocol is generally permissive
        "Mastodon": 10     # Varies by instance
    }
    
    return delays.get(platform, 15)  # Default 15 seconds