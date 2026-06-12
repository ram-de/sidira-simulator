### 1. User goal
The user goal is to watch content on Streamly, as evidenced by the presence of video playback information such as "Now playing · | HD 1080p | 00:07 | 52:00" on the `/watch/:id::overlay+s002039` and `/watch/:id::overlay+s9b8b43` screens.

### 2. Roles
The observed user roles are:
* member
* premium

Both roles have access to the watch capability, with similar screen layouts and functionality.

### 3. Flow per role
The flow for both member and premium roles is as follows:
1. The user enters the `/watch/:id::overlay+s002039` screen, which displays a cookie acceptance notice.
2. The user clicks the "Accept" button, transitioning to the `/watch/:id::overlay+s9b8b43` screen.
3. On both screens, the user can click the "← Back" button to exit the watch capability.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The watch capability depends on the browse capability, as evidenced by the exit transitions from `/watch/:id::overlay+s002039` to `/browse::s2c425e` (for member roles) and `/browse::s633472` (for premium roles) when the "← Back" button is clicked.

### 7. Implicit metric
The presence of video playback information such as "00:07 | 52:00" suggests that the system may be tracking video playback time, which could be an implicit metric for measuring user engagement with the watch capability.