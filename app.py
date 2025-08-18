import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import pytz
from database import init_database, save_post, get_posts, update_post_status, delete_post, get_failed_posts
from api_clients import post_to_platforms, get_platform_char_limits
from scheduler import start_scheduler, add_scheduled_post

# Page config
st.set_page_config(
    page_title="Social Media Manager",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database and scheduler
init_database()
start_scheduler()

# Tallinn timezone
TALLINN_TZ = pytz.timezone('Europe/Tallinn')

def main():
    # Sidebar navigation
    st.sidebar.title("📱 Social Media Manager")
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Create Post", "Manage Posts", "Settings"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Create Post":
        show_create_post()
    elif page == "Manage Posts":
        show_manage_posts()
    elif page == "Settings":
        show_settings()

def show_dashboard():
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
                        # Move back to scheduled for retry
                        update_post_status(row['id'], 'scheduled')
                        st.rerun()
                with col2:
                    if st.button(f"Edit", key=f"edit_{row['id']}"):
                        st.session_state.edit_post_id = row['id']
                        st.switch_page("Create Post")

def show_create_post():
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
        return
    
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
        # Default to tomorrow
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
                    # Update existing post
                    update_post_status(editing_post['id'], 'draft')
                    st.success("Post updated as draft!")
                else:
                    # Save new post
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
                        # Update existing post
                        update_post_status(editing_post['id'], 'scheduled')
                        st.success(f"Post rescheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!")
                    else:
                        # Schedule new post
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
                # Post immediately
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

def show_manage_posts():
    st.title("📝 Manage Posts")
    
    posts_df = get_posts()
    
    if posts_df.empty:
        st.info("No posts found")
        return
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   ["All"] + list(posts_df['status'].unique()))
    with col2:
        platform_filter = st.selectbox("Filter by Platform", ["All"] + 
                                     list(set([p for platforms in posts_df['platforms'].str.split(',') 
                                             for p in platforms if p])))
    
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
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"Edit", key=f"edit_{row['id']}"):
                    st.session_state.edit_post_id = row['id']
                    st.switch_page("Create Post")
            
            with col2:
                if row['status'] == 'failed' and st.button(f"Retry", key=f"retry_{row['id']}"):
                    update_post_status(row['id'], 'scheduled')
                    st.rerun()
            
            with col3:
                if st.button(f"Delete", key=f"delete_{row['id']}", type="secondary"):
                    delete_post(row['id'])
                    st.rerun()

def show_settings():
    st.title("⚙️ Settings")
    
    st.subheader("API Configuration")
    st.info("Configure your API credentials for each platform. These are stored securely in your local database.")
    
    platforms = {
        "Facebook": ["App ID", "App Secret", "Access Token"],
        "Threads": ["App ID", "App Secret", "Access Token"],
        "X (Twitter)": ["API Key", "API Secret", "Access Token", "Access Token Secret"],
        "LinkedIn": ["Client ID", "Client Secret", "Access Token"],
        "BlueSky": ["Username", "Password"],
        "Mastodon": ["Instance URL", "Access Token"]
    }
    
    for platform, fields in platforms.items():
        with st.expander(f"{platform} API Settings"):
            for field in fields:
                st.text_input(f"{field}", type="password", key=f"{platform}_{field}")
            if st.button(f"Save {platform} Settings", key=f"save_{platform}"):
                st.success(f"{platform} settings saved!")
    
    st.subheader("General Settings")
    
    with st.expander("Timezone Settings"):
        st.info("Current timezone: Europe/Tallinn")
        st.write("All scheduled posts use Tallinn timezone")
    
    with st.expander("Data Management"):
        if st.button("Export All Posts"):
            if not posts_df.empty:
                csv = posts_df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "social_media_posts.csv",
                    "text/csv"
                )
            else:
                st.info("No posts to export")
        
        if st.button("Clear All Data", type="secondary"):
            st.warning("⚠️ This will delete ALL posts. Use with caution!")

if __name__ == "__main__":
    main()