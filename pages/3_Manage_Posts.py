import streamlit as st
from utils.database import get_posts, update_post_status, delete_post

st.title("📝 Manage Posts")

posts_df = get_posts()

if posts_df.empty:
	st.info("No posts found")
	st.stop()

# Filters
col1, col2 = st.columns(2)
with col1:
	status_filter = st.selectbox("Filter by Status", ["All"] + list(posts_df['status'].unique()))
with col2:
	platform_filter = st.selectbox("Filter by Platform", ["All"] + list(set([p for platforms in posts_df['platforms'].str.split(',') for p in platforms if p])))

# Apply filters
filtered_df = posts_df.copy()
if status_filter != "All":
	filtered_df = filtered_df[filtered_df['status'] == status_filter]
if platform_filter != "All":
	filtered_df = filtered_df[filtered_df['platforms'].str.contains(platform_filter)]

# Display posts
for idx, row in filtered_df.iterrows():
	with st.expander(f"{row['status'].title()} - {row['created_at'][:16]}"):
		st.write("**Content:**")
		st.write(row['content'])
		st.write("**Platforms:**", row['platforms'])
		if row['scheduled_time']:
			st.write("**Scheduled:**", row['scheduled_time'][:16])
		col1, col2, col3 = st.columns(3)
		with col1:
			if st.button(f"Edit", key=f"edit_{row['id']}"):
				st.session_state.edit_post_id = row['id']
				st.switch_page("Create New Post")
		with col2:
			if row['status'] == 'failed' and st.button(f"Retry", key=f"retry_{row['id']}"):
				update_post_status(row['id'], 'scheduled')
				st.rerun()
		with col3:
			if st.button(f"Delete", key=f"delete_{row['id']}", type="secondary"):
				delete_post(row['id'])
				st.rerun()


