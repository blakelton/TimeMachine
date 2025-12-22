# Phase 5: Browser Notifications

> Push notifications for job completion and alerts

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: None (can start independently)

---

## Objective

Implement Web Push API notifications to alert users about job completion, errors, and system alerts even when the browser tab is closed or the user is away from the device.

## Prerequisites

- [ ] HTTPS deployment (required for Web Push)
- [ ] Service worker support in target browsers
- [ ] VAPID keys generated for push server

---

## Deliverables

### 1. Backend: VAPID Key Generation

**Purpose**: Generate and store VAPID keys for push authentication

**Tasks**:
- [ ] Generate VAPID key pair
- [ ] Store private key securely (environment variable)
- [ ] Expose public key via API for client subscription
- [ ] Add VAPID configuration to settings

**Setup**:
```bash
# Generate VAPID keys (one-time)
npx web-push generate-vapid-keys
```

**Environment**:
```bash
VAPID_PUBLIC_KEY=BExa...
VAPID_PRIVATE_KEY=QNW...
VAPID_SUBJECT=mailto:admin@example.com
```

**Files**:
- `backend/app/core/config.py` (add VAPID settings)
- `deploy/timemachine.env.example` (add VAPID placeholders)

---

### 2. Backend: Subscription Model

**Purpose**: Store push subscription information

**Tasks**:
- [ ] Create PushSubscription database model
- [ ] Store endpoint, keys, and user preferences
- [ ] Handle subscription updates
- [ ] Clean up expired subscriptions

**Schema**:
```python
class PushSubscription:
    id: int
    endpoint: str
    p256dh_key: str
    auth_key: str
    user_agent: str | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None

    # Notification preferences
    notify_job_complete: bool
    notify_job_failed: bool
    notify_alerts: bool
    notify_disk_low: bool
```

**Files**:
- `backend/app/db/models/notifications.py` (new)
- `backend/app/db/repositories/notifications.py` (new)

---

### 3. Backend: Push Service

**Purpose**: Send push notifications

**Tasks**:
- [ ] Add pywebpush dependency
- [ ] Create push service with retry logic
- [ ] Handle expired/invalid subscriptions
- [ ] Implement notification types
- [ ] Queue notifications for reliability

**Interface**:
```python
class PushService:
    async def send(subscription_id: int, notification: Notification) -> bool
    async def broadcast(notification: Notification, filter: NotificationFilter) -> int
    async def cleanup_expired() -> int

@dataclass
class Notification:
    title: str
    body: str
    icon: str | None
    badge: str | None
    tag: str | None  # Replaces notifications with same tag
    data: dict | None  # Custom data for click handling
    actions: list[NotificationAction] | None
```

**Files**:
- `backend/app/services/notifications/push.py` (new)
- `backend/requirements.txt` (add pywebpush)

---

### 4. Backend: Notification Triggers

**Purpose**: Send notifications on events

**Tasks**:
- [ ] Trigger on job completion
- [ ] Trigger on job failure
- [ ] Trigger on temperature alerts
- [ ] Trigger on low disk space
- [ ] Respect per-subscription preferences

**Events**:
```python
# Job completed
{
    "title": "Recording Complete",
    "body": "Camera 1 - 30 minute recording saved",
    "tag": "job-complete-123",
    "data": {"type": "job", "id": 123, "action": "view"}
}

# Job failed
{
    "title": "Recording Failed",
    "body": "Camera 1 - Disk space exhausted",
    "tag": "job-failed-124"
}

# Temperature alert
{
    "title": "Temperature Alert",
    "body": "Chamber at 32°C - Above limit of 30°C",
    "tag": "temp-alert"
}
```

**Files**:
- `backend/app/services/notifications/triggers.py` (new)
- Integrate with job service, temperature service

---

### 5. Backend: API Endpoints

**Purpose**: Manage push subscriptions

**Endpoints**:
```
GET  /api/v1/notifications/vapid-key     → Get public VAPID key
POST /api/v1/notifications/subscribe     → Register subscription
PUT  /api/v1/notifications/subscribe     → Update subscription preferences
DELETE /api/v1/notifications/subscribe   → Unsubscribe
GET  /api/v1/notifications/preferences   → Get current preferences
POST /api/v1/notifications/test          → Send test notification
```

**Tasks**:
- [ ] Create notifications router
- [ ] Implement subscription management
- [ ] Add test notification endpoint
- [ ] Validate subscription data

**Files**:
- `backend/app/api/routes/notifications.py` (new)
- `backend/app/schemas/notifications.py` (new)

---

### 6. Frontend: Service Worker

**Purpose**: Receive push notifications in background

**Tasks**:
- [ ] Create service worker for push handling
- [ ] Handle notification display
- [ ] Handle notification click (open app, navigate)
- [ ] Handle notification close
- [ ] Register service worker on app load

**Service Worker**:
```javascript
// sw.js
self.addEventListener('push', (event) => {
    const data = event.data.json();
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon || '/icon-192.png',
            badge: '/badge-72.png',
            tag: data.tag,
            data: data.data,
            actions: data.actions
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const data = event.notification.data;
    if (data?.action === 'view' && data?.type === 'job') {
        event.waitUntil(
            clients.openWindow(`/jobs/${data.id}`)
        );
    }
});
```

**Files**:
- `frontend/public/sw.js` (new)
- `frontend/src/serviceWorkerRegistration.ts` (new)

---

### 7. Frontend: Permission Flow

**Purpose**: Request notification permission from user

**Tasks**:
- [ ] Create permission request component
- [ ] Handle "denied" state gracefully
- [ ] Show explanation of benefits
- [ ] Don't prompt on every page load
- [ ] Persist user's choice

**Component**:
```tsx
<NotificationPermission
  onGranted={() => subscribeToNotifications()}
  onDenied={() => showDeniedMessage()}
/>
```

**Files**:
- `frontend/src/components/NotificationPermission.tsx` (new)
- `frontend/src/hooks/useNotifications.ts` (new)

---

### 8. Frontend: Subscription Management

**Purpose**: Subscribe/unsubscribe from push notifications

**Tasks**:
- [ ] Create subscription hook
- [ ] Handle browser Push API
- [ ] Send subscription to backend
- [ ] Handle subscription refresh

**Hook**:
```typescript
const useNotifications = () => {
    const [isSubscribed, setIsSubscribed] = useState(false);
    const [isSupported, setIsSupported] = useState(false);

    const subscribe = async () => {...};
    const unsubscribe = async () => {...};

    return { isSubscribed, isSupported, subscribe, unsubscribe };
};
```

**Files**:
- `frontend/src/hooks/useNotifications.ts` (extend)

---

### 9. Frontend: Preferences Panel

**Purpose**: Configure notification preferences

**Tasks**:
- [ ] Create `NotificationSettings.tsx` component
- [ ] Toggle for each notification type
- [ ] Test notification button
- [ ] Show subscription status
- [ ] Add to Settings page

**Preferences**:
- Job completion notifications (on/off)
- Job failure notifications (on/off)
- Temperature alerts (on/off)
- Disk space warnings (on/off)

**Files**:
- `frontend/src/components/settings/NotificationSettings.tsx` (new)
- `frontend/src/pages/SystemPage.tsx` (integrate)

---

### 10. Frontend: In-App Notification Banner

**Purpose**: Prompt users to enable notifications

**Tasks**:
- [ ] Create dismissible banner component
- [ ] Show when notifications not enabled
- [ ] Don't show if previously dismissed
- [ ] Link to settings

**Files**:
- `frontend/src/components/NotificationBanner.tsx` (new)
- `frontend/src/pages/HomePage.tsx` (integrate)

---

## Browser Compatibility

| Browser | Desktop | Mobile | Notes |
|---------|---------|--------|-------|
| Chrome | ✅ | ✅ | Full support |
| Firefox | ✅ | ✅ | Full support |
| Safari | ✅ | ✅ | Requires macOS 13+ or iOS 16.4+ |
| Edge | ✅ | ✅ | Full support |

---

## Testing Requirements

### Backend Tests
- [ ] Unit tests for push service
- [ ] Test subscription CRUD
- [ ] Test notification triggers
- [ ] API endpoint tests

### Frontend Tests
- [ ] Component tests for NotificationSettings
- [ ] Hook tests for useNotifications
- [ ] Service worker registration tests

### Manual Tests
- [ ] Permission request flow
- [ ] Notification display (tab open)
- [ ] Notification display (tab closed)
- [ ] Notification click navigation
- [ ] Different browsers

---

## Quality Gate

- [ ] Notifications work when tab is closed
- [ ] Preferences respected
- [ ] No HIGH or CRITICAL issues
- [ ] Graceful fallback when not supported

---

## Success Criteria

1. Notifications appear when browser tab is closed
2. Users can subscribe/unsubscribe per event type
3. Works on mobile browsers
4. Graceful degradation when unsupported
5. No spam; only important events trigger

---

## Notes

- HTTPS required for Web Push (use nginx SSL)
- Generate new VAPID keys for each deployment
- Consider rate limiting notifications
- Safari on iOS requires specific handling

---

**Estimated Effort**: 2-3 days
**Dependencies**: None
**Parallel**: Can run alongside any phase
