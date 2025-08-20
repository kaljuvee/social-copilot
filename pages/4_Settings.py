import streamlit as st
import os
import json
from utils.database import get_posts, get_api_credentials, save_api_credentials

st.title("⚙️ Settings")

st.subheader("API Configuration")
st.info("Configure your API credentials for each platform. Values from the environment are used as defaults, and any changes here override them and are stored locally.")

platforms = {
	"Facebook": ["app_id", "app_secret", "access_token"],
	"Threads": ["app_id", "app_secret", "access_token"],
	"X (Twitter)": ["api_key", "api_secret", "access_token", "access_token_secret", "bearer_token"],
	"LinkedIn": ["client_id", "client_secret", "access_token", "person_urn"],
	"BlueSky": ["username", "password"],
	"Mastodon": ["instance_url", "access_token"]
}

env_keys = {
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

for platform, fields in platforms.items():
	with st.expander(f"{platform} API Settings"):
		default_values = {}
		db_json = get_api_credentials(platform)
		if db_json:
			try:
				default_values = json.loads(db_json) or {}
			except Exception:
				default_values = {}
		for field in fields:
			if field not in default_values:
				env_name = env_keys.get(platform, {}).get(field)
				if env_name and os.getenv(env_name):
					default_values[field] = os.getenv(env_name)

		updated_values = {}
		for field in fields:
			updated_values[field] = st.text_input(
				f"{field}", value=default_values.get(field, ""), type="password", key=f"{platform}_{field}"
			)

		if st.button(f"Save {platform} Settings", key=f"save_{platform}"):
			try:
				save_api_credentials(platform, json.dumps(updated_values))
				st.success(f"{platform} settings saved!")
			except Exception as e:
				st.error(f"Failed to save {platform} settings: {e}")

st.subheader("General Settings")

with st.expander("Timezone Settings"):
	current_tz = os.getenv('TIMEZONE', 'Europe/Tallinn')
	st.info(f"Current timezone: {current_tz}")
	st.write("All scheduled posts use the configured timezone")

with st.expander("Data Management"):
	if st.button("Export All Posts"):
		export_df = get_posts()
		if not export_df.empty:
			csv = export_df.to_csv(index=False)
			st.download_button(
				"Download CSV",
				csv,
				"social_media_posts.csv",
				"text/csv"
			)
		else:
			st.info("No posts to export")


