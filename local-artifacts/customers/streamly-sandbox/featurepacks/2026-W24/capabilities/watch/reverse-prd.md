### 1. User goal
The user goal is to watch content on Streamly, as evidenced by the presence of video playback information such as "Now playing · | HD 1080p | 00:07 | 52:00" on the `/watch/:id::overlay+s002039` and `/watch/:id::overlay+s9b8b43` screens.

### 2. Roles
The observed user roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles follow the same flow:
1. Enter the `/watch/:id::overlay+s002039` screen, which displays a cookie acceptance notice.
2. Click the 'Accept' button to transition to the `/watch/:id::overlay+s9b8b43` screen, which appears to be the main video playback screen.
Both roles can also exit the watch capability by clicking the '← Back' button, but the destination screen differs between members (`/browse::s2c425e`) and premiums (`/browse::s633472`).

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The watch capability depends on the browse capability, as evidenced by the exit transitions from `/watch/:id::overlay+s002039` to `/browse::s2c425e` (for members) and `/browse::s633472` (for premiums) when the '← Back' button is clicked.

### 7. Implicit metric
The presence of video playback information such as "Now playing · | HD 1080p | 00:07 | 52:00" and the ability to transition between different video quality options (e.g., HD 1080p and 4K Ultra HD) implies that video playback quality and engagement metrics (e.g., watch time, playback quality selection) may be important metrics for this capability.