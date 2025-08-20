import streamlit as st
from utils.database import get_posts, get_failed_posts, update_post_status

st.title("📊 Dashboard")

# Get posts data
posts_df = get_posts()
failed_posts = get_failed_posts()

# Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
	scheduled_count = len(posts_df[posts_df['status'] == 'scheduled']) if not posts_df.empty else 0
	st.metric("Scheduled Posts", scheduled_count)

with col2:
	posted_count = len(posts_df[posts_df['status'] == 'posted']) if not posts_df.empty else 0
	st.metric("Posted Today", posted_count)

with col3:
	failed_count = len(failed_posts) if not failed_posts.empty else 0
	st.metric("Failed Posts", failed_count, delta=f"-{failed_count}" if failed_count > 0 else None)

with col4:
	total_count = len(posts_df) if not posts_df.empty else 0
	st.metric("Total Posts", total_count)

# Upcoming posts
st.subheader("📅 Upcoming Posts")
if not posts_df.empty:
	upcoming = posts_df[posts_df['status'] == 'scheduled'].head(10)
	if not upcoming.empty:
		for idx, row in upcoming.iterrows():
			with st.container():
				col1, col2, col3 = st.columns([3, 2, 1])
				with col1:
					st.write(f"**{row['scheduled_time'][:16]}**")
					st.write(row['content'][:100] + "..." if len(row['content']) > 100 else row['content'])
				with col2:
					platforms = row['platforms'].split(',') if row['platforms'] else []
					st.write("Platforms: " + ", ".join(platforms))
				with col3:
					st.write(f"Status: {row['status']}")
	else:
		st.info("No upcoming posts scheduled")
else:
	st.info("No posts created yet")

# Failed posts section
if not failed_posts.empty:
	st.subheader("❌ Failed Posts")
	for idx, row in failed_posts.iterrows():
		with st.expander(f"Failed: {row['created_at'][:16]}"):
			st.write("**Content:**", row['content'])
			st.write("**Platforms:**", row['platforms'])
			st.write("**Error:**", row.get('error_message', 'Unknown error'))
			col1, col2 = st.columns(2)
			with col1:
				if st.button(f"Retry", key=f"retry_{row['id']}"):
					update_post_status(row['id'], 'scheduled')
					st.rerun()
			with col2:
				if st.button(f"Edit", key=f"edit_{row['id']}"):
					st.session_state.edit_post_id = row['id']
					st.switch_page("Create New Post")


