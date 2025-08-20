import threading
import time
from datetime import datetime, timezone
from typing import Optional
import pytz
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import streamlit as st
from utils.database import get_post_by_id, update_post_status, get_scheduled_posts, add_to_queue, get_queue_items, update_queue_status
from utils.api_clients import post_to_single_platform, get_rate_limit_delay

# Global scheduler instance
scheduler = None
TALLINN_TZ = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Tallinn'))

def start_scheduler():
    """Initialize and start the background scheduler"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=TALLINN_TZ)
        scheduler.start()
        
        # Start the queue processor
        start_queue_processor()
        
        # Reschedule any existing scheduled posts
        reschedule_existing_posts()

def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None

def add_scheduled_post(post_id: int, scheduled_datetime: datetime):
    """Add a post to the scheduler"""
    global scheduler
    
    if scheduler is None:
        start_scheduler()
    
    # Convert to UTC for scheduler
    utc_datetime = scheduled_datetime.astimezone(timezone.utc)
    
    job_id = f"post_{post_id}"
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    # Add new job
    scheduler.add_job(
        func=process_scheduled_post,
        trigger=DateTrigger(run_date=utc_datetime),
        args=[post_id],
        id=job_id,
        replace_existing=True
    )

def process_scheduled_post(post_id: int):
    """Process a scheduled post when its time comes"""
    try:
        post = get_post_by_id(post_id)
        if not post or post['status'] != 'scheduled':
            return
        
        # Update status to posting
        update_post_status(post_id, 'posting')
        
        # Get platforms
        platforms = post['platforms'].split(',')
        content = post['content']
        
        # Add to queue for each platform
        for platform in platforms:
            add_to_queue(post_id, platform.strip())
        
        # The queue processor will handle the actual posting
        
    except Exception as e:
        # Mark as failed if something goes wrong
        update_post_status(post_id, 'failed', f"Scheduling error: {str(e)}")

def start_queue_processor():
    """Start the background queue processor"""
    def queue_worker():
        """Background worker to process the posting queue"""
        platforms = ["Facebook", "Threads", "X (Twitter)", "LinkedIn", "BlueSky", "Mastodon"]
        
        while True:
            try:
                for platform in platforms:
                    process_platform_queue(platform)
                
                # Sleep for 30 seconds between queue checks
                time.sleep(30)
                
            except Exception as e:
                print(f"Queue processor error: {e}")
                time.sleep(60)  # Longer sleep on error
    
    # Start worker thread
    worker_thread = threading.Thread(target=queue_worker, daemon=True)
    worker_thread.start()

def process_platform_queue(platform: str):
    """Process pending items for a specific platform"""
    try:
        # Get pending items for this platform
        queue_items = get_queue_items(platform, limit=5)
        
        if queue_items.empty:
            return
        
        rate_limit_delay = get_rate_limit_delay(platform)
        
        for idx, item in queue_items.iterrows():
            try:
                # Get the post content
                content = item['content']
                post_id = item['post_id']
                queue_id = item['id']
                
                # Update queue status to processing
                update_queue_status(queue_id, 'processing')
                
                # Attempt to post
                success, error_message = post_to_single_platform(content, platform)
                
                if success:
                    # Mark queue item as completed
                    update_queue_status(queue_id, 'completed')
                    
                    # Check if all platforms for this post are done
                    check_post_completion(post_id)
                    
                else:
                    # Handle failure
                    retry_count = item.get('retry_count', 0) + 1
                    
                    if retry_count <= 3:  # Max 3 retries
                        # Mark for retry
                        update_queue_status(queue_id, 'pending', retry_count)
                    else:
                        # Max retries reached, mark as failed
                        update_queue_status(queue_id, 'failed', retry_count)
                        update_post_status(post_id, 'failed', f"{platform}: {error_message}")
                
                # Rate limiting delay
                time.sleep(rate_limit_delay)
                
            except Exception as e:
                # Mark queue item as failed
                update_queue_status(item['id'], 'failed')
                print(f"Error processing queue item {item['id']}: {e}")
    
    except Exception as e:
        print(f"Error processing {platform} queue: {e}")

def check_post_completion(post_id: int):
    """Check if all platforms for a post have completed and update post status"""
    try:
        from utils.database import get_queue_items
        import sqlite3
        
        # Check queue status for all platforms of this post
        conn = sqlite3.connect('social_media_posts.db')
        c = conn.cursor()
        
        c.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM post_queue 
            WHERE post_id = ?
        """, (post_id,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            total, completed, failed = result
            
            if completed + failed == total:  # All done
                if completed == total:  # All successful
                    update_post_status(post_id, 'posted')
                elif completed > 0:  # Partial success
                    update_post_status(post_id, 'partial', f"Posted to {completed}/{total} platforms")
                else:  # All failed
                    update_post_status(post_id, 'failed', "Failed to post to all platforms")
    
    except Exception as e:
        print(f"Error checking post completion: {e}")

def reschedule_existing_posts():
    """Reschedule any existing scheduled posts after app restart"""
    try:
        scheduled_posts = get_scheduled_posts()
        
        for idx, post in scheduled_posts.iterrows():
            if post['scheduled_time']:
                try:
                    # Parse the scheduled time
                    scheduled_dt = datetime.fromisoformat(post['scheduled_time'])
                    
                    # Make sure it's timezone-aware
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = TALLINN_TZ.localize(scheduled_dt)
                    
                    # Only reschedule future posts
                    if scheduled_dt > datetime.now(TALLINN_TZ):
                        add_scheduled_post(post['id'], scheduled_dt)
                    else:
                        # Past posts should be marked as failed
                        update_post_status(post['id'], 'failed', "Missed scheduled time")
                
                except Exception as e:
                    print(f"Error rescheduling post {post['id']}: {e}")
                    update_post_status(post['id'], 'failed', f"Rescheduling error: {str(e)}")
    
    except Exception as e:
        print(f"Error during reschedule: {e}")

def remove_scheduled_post(post_id: int):
    """Remove a post from the scheduler"""
    global scheduler
    
    if scheduler:
        job_id = f"post_{post_id}"
        try:
            scheduler.remove_job(job_id)
        except:
            pass  # Job might not exist

def get_scheduler_status():
    """Get current scheduler status for debugging"""
    global scheduler
    
    if scheduler is None:
        return "Scheduler not started"
    
    if scheduler.running:
        jobs = scheduler.get_jobs()
        return f"Scheduler running with {len(jobs)} jobs"
    else:
        return "Scheduler stopped"

def pause_scheduler():
    """Pause the scheduler"""
    global scheduler
    if scheduler:
        scheduler.pause()

def resume_scheduler():
    """Resume the scheduler"""
    global scheduler
    if scheduler:
        scheduler.resume()

# Ensure scheduler starts when module is imported
if 'scheduler_started' not in st.session_state:
    st.session_state.scheduler_started = True
    start_scheduler()