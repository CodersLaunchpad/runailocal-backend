from enum import Enum

class ActionType(str, Enum):
    """User action types for behavior tracking"""
    VIEW = "view"
    LIKE = "like"
    UNLIKE = "unlike"
    BOOKMARK = "bookmark"
    UNBOOKMARK = "unbookmark"
    SHARE = "share"
    COMMENT = "comment"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    SEARCH = "search"
    CLICK = "click"
    SCROLL = "scroll"
    READ_TIME = "read_time"

class ReadingFrequency(str, Enum):
    """User reading frequency preferences"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    OCCASIONAL = "occasional"

class ContentLength(str, Enum):
    """User content length preferences"""
    SHORT = "short"  # < 5 min read
    MEDIUM = "medium"  # 5-15 min read
    LONG = "long"  # > 15 min read
    ANY = "any"

class SubscriptionTier(str, Enum):
    """User subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class ContentAccess(str, Enum):
    """Content access levels"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"