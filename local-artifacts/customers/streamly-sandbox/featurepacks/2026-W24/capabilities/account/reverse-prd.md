### 1. User goal
Manage my Streamly account settings.

### 2. Roles
The observed roles are:
- member
- premium

### 3. Flow per role
Both member and premium roles can access the account settings through the `/account` route. The flow involves navigating through the account settings screens, specifically:
- `/account::s4058eb`
- `/account::saca983`

These screens contain headings for Account, Membership, Playback settings, and Security. Users can transition between these screens by clicking the 'Accept' button.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The account capability has dependencies on the following capabilities:
- Browse (`/browse`)
- Search (`/search`)
- My List (`/my-list`)
- Kids (`/kids`)
- Account plan management (`/account/plan`)
- Sign out (`/`)

These dependencies are observed through the various links and buttons on the account settings screens that navigate to these other capabilities.

### 7. Implicit metric
_(no evidence observed)_