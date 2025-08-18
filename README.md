# Social Media Manager

A comprehensive Streamlit application for managing and scheduling posts across multiple social media platforms including Facebook, Threads, X (Twitter), LinkedIn, BlueSky, and Mastodon.

## Features

- **Multi-Platform Posting**: Cross-post content to Facebook, Threads, X, LinkedIn, BlueSky, and Mastodon
- **Scheduling System**: Schedule posts for future publishing with Tallinn timezone support
- **Queue Management**: Built-in rate limiting and retry mechanism for failed posts
- **Dashboard**: Overview of scheduled, posted, and failed posts
- **Content Management**: Create, edit, and delete posts with platform-specific character limits
- **API Integration**: Direct API connections for automated posting
- **Failed Post Recovery**: Edit and retry failed posts

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd streamlit-test
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Setup

### API Configuration

Before using the application, you need to configure API credentials for each platform you want to use:

#### Facebook
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create an app and get your App ID, App Secret, and Access Token
3. Enter these in the Settings page

#### X (Twitter)
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create an app and get your Bearer Token
3. Enter in the Settings page

#### LinkedIn
1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Create an app and get your Client ID, Client Secret, and Access Token
3. Enter in the Settings page

#### BlueSky
1. You need your BlueSky username and password
2. Enter in the Settings page

#### Mastodon
1. Go to your Mastodon instance settings
2. Generate an Access Token
3. Enter your instance URL and Access Token in the Settings page

#### Threads
- Threads API is still in development by Meta
- Configuration placeholder is available for future implementation

## Usage

### Dashboard
- View metrics for all your posts
- See upcoming scheduled posts
- Manage failed posts that need attention

### Create Post
1. Select target platforms using checkboxes
2. Enter your post content (character limits are enforced per platform)
3. Choose to save as draft, schedule for later, or post immediately
4. For scheduled posts, select date and time (Tallinn timezone)

### Manage Posts
- View all posts with filtering options
- Edit existing posts
- Retry failed posts
- Delete unwanted posts

### Settings
- Configure API credentials for each platform
- Export post data
- Manage application settings

## Technical Details

### Architecture
- **Frontend**: Streamlit web application
- **Database**: SQLite for local data storage
- **Scheduling**: APScheduler with background processing
- **APIs**: Direct integration with platform APIs
- **Queue System**: Handles rate limiting and retries automatically

### Database Schema
- `posts`: Main posts table with content, platforms, scheduling info
- `api_credentials`: Encrypted storage of API keys
- `post_queue`: Queue system for rate limiting and retries

### File Structure
```
├── app.py              # Main Streamlit application
├── database.py         # Database functions and schema
├── api_clients.py      # Platform API client implementations
├── scheduler.py        # Background scheduling and queue processing
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Rate Limiting

The application automatically handles rate limiting for each platform:
- Facebook: 30 second delays
- X (Twitter): 5 second delays
- LinkedIn: 60 second delays
- BlueSky: 5 second delays
- Mastodon: 10 second delays
- Threads: 10 second delays

Failed posts are automatically retried up to 3 times before being marked as failed.

## Timezone Support

All scheduling uses Europe/Tallinn timezone. The application automatically converts times for proper scheduling and display.

## Security Notes

- API credentials are stored locally in the SQLite database
- No data is sent to external servers except the social media platforms themselves
- Use environment variables or secure credential storage for production deployments

## Troubleshooting

### Common Issues

1. **Posts not appearing**: Check API credentials and platform-specific rate limits
2. **Scheduling not working**: Ensure the application remains running for background processing
3. **Character limit errors**: Each platform has different limits - check the character counters
4. **Failed posts**: Check the dashboard for error messages and retry functionality

### Debug Information

The application includes built-in error handling and logging. Failed posts include error messages to help diagnose issues.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. See the license file for details.

## Support

For issues and questions, please create an issue in the GitHub repository.