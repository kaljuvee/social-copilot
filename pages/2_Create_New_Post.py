import streamlit as st
from datetime import datetime
import pytz
import os
from utils.database import get_posts, save_post, update_post_status
from utils.api_clients import get_platform_char_limits, post_to_platforms
from utils.scheduler import add_scheduled_post

TALLINN_TZ = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Tallinn'))

st.title("✍️ Create New Post")

# Check if editing existing post
editing_post = None
if 'edit_post_id' in st.session_state:
	posts_df = get_posts()
	editing_post = posts_df[posts_df['id'] == st.session_state.edit_post_id]
	if not editing_post.empty:
		editing_post = editing_post.iloc[0]
	else:
		del st.session_state.edit_post_id

# Platform selection
st.subheader("Select Platforms")
platforms = ["Facebook", "Threads", "X (Twitter)", "LinkedIn", "BlueSky", "Mastodon"]

col1, col2, col3 = st.columns(3)
selected_platforms = []

for i, platform in enumerate(platforms):
	with [col1, col2, col3][i % 3]:
		default_checked = platform in editing_post['platforms'].split(',') if editing_post is not None else False
		if st.checkbox(platform, key=f"platform_{platform}", value=default_checked):
			selected_platforms.append(platform)

if not selected_platforms:
	st.warning("Please select at least one platform")
	st.stop()

# Content input with character limits
st.subheader("Post Content")
char_limits = get_platform_char_limits()
min_limit = min([char_limits.get(p, 280) for p in selected_platforms])

default_content = editing_post['content'] if editing_post is not None else ""
content = st.text_area(
	f"Post content (max {min_limit} characters for selected platforms)",
	value=default_content,
	height=150,
	max_chars=min_limit
)

# Show character count for each platform
if content:
	st.write("**Character count by platform:**")
	for platform in selected_platforms:
		limit = char_limits.get(platform, 280)
		count = len(content)
		color = "green" if count <= limit else "red"
		st.write(f"- {platform}: {count}/{limit} characters", color=color)

# Scheduling
st.subheader("Schedule Post")

col1, col2 = st.columns(2)
with col1:
	default_date = datetime.now(TALLINN_TZ).date()
	if editing_post is not None and editing_post['scheduled_time']:
		default_date = datetime.fromisoformat(editing_post['scheduled_time']).date()
	
	scheduled_date = st.date_input(
		"Date",
		value=default_date,
		min_value=datetime.now(TALLINN_TZ).date()
	)

with col2:
	default_time = datetime.now(TALLINN_TZ).time().replace(second=0, microsecond=0)
	if editing_post is not None and editing_post['scheduled_time']:
		default_time = datetime.fromisoformat(editing_post['scheduled_time']).time()
	
	scheduled_time = st.time_input("Time (Tallinn timezone)", value=default_time)

# Combine date and time
scheduled_datetime = TALLINN_TZ.localize(
	datetime.combine(scheduled_date, scheduled_time)
)

# Action buttons
col1, col2, col3 = st.columns(3)

with col1:
	if st.button("💾 Save as Draft", type="secondary"):
		if content and selected_platforms:
			if editing_post is not None:
				update_post_status(editing_post['id'], 'draft')
				st.success("Post updated as draft!")
			else:
				save_post(
					content=content,
					platforms=','.join(selected_platforms),
					scheduled_time=scheduled_datetime.isoformat(),
					status='draft'
				)
				st.success("Post saved as draft!")
			if 'edit_post_id' in st.session_state:
				del st.session_state.edit_post_id
			st.rerun()

with col2:
	if st.button("📅 Schedule Post", type="primary"):
		if content and selected_platforms:
			if scheduled_datetime > datetime.now(TALLINN_TZ):
				if editing_post is not None:
					update_post_status(editing_post['id'], 'scheduled')
					st.success(f"Post rescheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!")
				else:
					post_id = save_post(
						content=content,
						platforms=','.join(selected_platforms),
						scheduled_time=scheduled_datetime.isoformat(),
						status='scheduled'
					)
					add_scheduled_post(post_id, scheduled_datetime)
					st.success(f"Post scheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!")
				if 'edit_post_id' in st.session_state:
					del st.session_state.edit_post_id
				st.rerun()
			else:
				st.error("Scheduled time must be in the future")

with col3:
	if st.button("🚀 Post Now"):
		if content and selected_platforms:
			success, errors = post_to_platforms(content, selected_platforms)
			if success:
				save_post(
					content=content,
					platforms=','.join(selected_platforms),
					scheduled_time=datetime.now(TALLINN_TZ).isoformat(),
					status='posted'
				)
				st.success("Posted successfully to all platforms!")
			else:
				save_post(
					content=content,
					platforms=','.join(selected_platforms),
					scheduled_time=datetime.now(TALLINN_TZ).isoformat(),
					status='failed',
					error_message=str(errors)
				)
				st.error("Some posts failed. Check the Manage Posts section.")
			if 'edit_post_id' in st.session_state:
				del st.session_state.edit_post_id
			st.rerun()


