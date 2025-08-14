# Social Media Links for User Profiles

This document describes the implementation of social media links functionality for user profiles in the RunAI Local Backend.

## Overview

Users can now add social media links to their profiles, including platforms like LinkedIn, GitHub, Instagram, Twitter, etc. These links are displayed on user profiles and can be updated by users.

## Implementation Details

### Models

#### SocialMediaLink
```python
class SocialMediaLink(BaseModel):
    label: str    # Human-readable platform name (e.g., "LinkedIn", "Instagram")
    icon: str     # Icon identifier (e.g., "linkedin", "instagram", "github")
    url: str      # Full profile URL
```

#### User Models
The following user models now include social media links:
- `UserBase` - Base user fields
- `UserCreate` - For creating new users
- `UserUpdate` - For updating existing users
- `UserResponse` - For API responses
- `UserInDB` - Database representation

### Database Schema

The `users` collection now includes these fields:
- `bio`: Optional string for user biography
- `date_of_birth`: Optional string for user's date of birth
- `social_media_links`: Array of social media link objects

### API Endpoints

#### Create User
- **POST** `/users/register`
- New optional fields: `bio`, `date_of_birth`, `social_media_links`
- `social_media_links` should be sent as a JSON string

#### Update User Profile
- **PUT** `/users/me`
- New optional fields: `bio`, `date_of_birth`, `social_media_links`
- `social_media_links` should be sent as a JSON string

#### Admin Update User
- **PUT** `/users/{user_id}`
- Same fields as regular update, but for admin use

#### Get User Profile
- **GET** `/users/me`
- **GET** `/users/{user_id}`
- Returns user data including bio, date_of_birth, and social_media_links

### Example Usage

#### Creating a User with Social Media Links
```bash
curl -X POST "http://localhost:8000/users/register" \
  -F "username=johndoe" \
  -F "email=john@example.com" \
  -F "password=password123" \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "bio=Software developer passionate about clean code" \
  -F "social_media_links=[{\"label\":\"LinkedIn\",\"icon\":\"linkedin\",\"url\":\"https://www.linkedin.com/in/johndoe\"},{\"label\":\"GitHub\",\"icon\":\"github\",\"url\":\"https://github.com/johndoe\"}]"
```

#### Updating User Profile
```bash
curl -X PUT "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "bio=Updated bio text" \
  -F "social_media_links=[{\"label\":\"Instagram\",\"icon\":\"instagram\",\"url\":\"https://www.instagram.com/johndoe\"}]"
```

### Social Media Links Format

The `social_media_links` field expects a JSON array of objects with this structure:

```json
[
  {
    "label": "LinkedIn",
    "icon": "linkedin",
    "url": "https://www.linkedin.com/in/username"
  },
  {
    "label": "GitHub",
    "icon": "github", 
    "url": "https://github.com/username"
  },
  {
    "label": "Instagram",
    "icon": "instagram",
    "url": "https://www.instagram.com/username"
  }
]
```

### Supported Icons

Common icon identifiers that can be used:
- `linkedin` - LinkedIn
- `github` - GitHub
- `instagram` - Instagram
- `twitter` - Twitter/X
- `facebook` - Facebook
- `youtube` - YouTube
- `website` - Personal website
- `blog` - Blog
- `portfolio` - Portfolio

### Migration

For existing users, a migration script is provided:
```bash
python mongo/054_add_user_profile_fields.py
```

This script will:
1. Add `bio` field with empty string default
2. Add `date_of_birth` field with `null` default
3. Add `social_media_links` field with empty array default
4. Add migration timestamp

### Frontend Integration

When displaying user profiles, frontend applications should:

1. **Display Bio**: Show the user's bio text in a dedicated section
2. **Display Date of Birth**: Format and display the date appropriately
3. **Display Social Media Links**: Render each link with appropriate icons and make them clickable

Example frontend structure:
```html
<div class="user-profile">
  <div class="user-info">
    <h2>{{ user.first_name }} {{ user.last_name }}</h2>
    <p class="username">@{{ user.username }}</p>
  </div>
  
  <div class="user-bio" v-if="user.bio">
    <h3>About</h3>
    <p>{{ user.bio }}</p>
  </div>
  
  <div class="user-details" v-if="user.date_of_birth">
    <h3>Details</h3>
    <p>Born: {{ formatDate(user.date_of_birth) }}</p>
  </div>
  
  <div class="social-links" v-if="user.social_media_links.length">
    <h3>Connect</h3>
    <div class="social-icons">
      <a v-for="link in user.social_media_links" 
         :key="link.icon"
         :href="link.url" 
         target="_blank"
         :title="link.label">
        <i :class="'icon-' + link.icon"></i>
      </a>
    </div>
  </div>
</div>
```

### Error Handling

The API includes validation for:
- JSON format of social media links
- Required fields for user creation
- User authentication and authorization

Common error responses:
- `400 Bad Request`: Invalid JSON format for social media links
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions for admin operations

### Testing

A test script is provided to verify the functionality:
```bash
python test_social_media_links.py
```

This script tests:
- Model creation and validation
- JSON serialization
- API model compatibility

## Future Enhancements

Potential improvements for future versions:
1. **URL Validation**: Add proper URL format validation
2. **Icon Validation**: Restrict icon values to predefined list
3. **Link Verification**: Add option to verify social media links
4. **Analytics**: Track clicks on social media links
5. **Custom Icons**: Allow users to upload custom icons
6. **Link Categories**: Group links by category (professional, personal, etc.)
