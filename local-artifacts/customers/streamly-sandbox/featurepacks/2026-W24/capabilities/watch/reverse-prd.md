### 1. User goal
The user goal is to watch content on Streamly, as evidenced by the presence of video playback controls (e.g., "Now playing ·", "HD 1080p", "00:07", "52:00") on the `/watch/:id` screens.

### 2. Roles
The observed user roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles follow the same flow:
1. Enter the `/watch/:id::overlay+s002039` screen, which displays a cookie acceptance notice.
2. Click the "Accept" button to transition to the `/watch/:id::overlay+s9b8b43` screen, which displays the video playback controls, including the option to switch to "4K Ultra HD" (only visible after accepting cookies).
3. Both roles can exit the watch capability by clicking the "← Back" button, which redirects them to the `/browse` capability (with different route parameters for member and premium roles).

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The watch capability depends on the browse capability, as evidenced by the exit transitions from `/watch/:id::overlay+s002039` to `/browse::s2c425e` (for member roles) and `/browse::s633472` (for premium roles) when the "← Back" button is clicked.

### 7. Implicit metric
The presence of video playback controls and the display of playback time (e.g., "00:07", "52:00") suggests that an implicit metric for this capability could be video engagement or watch time.