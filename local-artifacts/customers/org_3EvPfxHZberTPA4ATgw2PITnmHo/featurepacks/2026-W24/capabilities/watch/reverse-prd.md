### 1. User goal
Watch content on Streamly, specifically videos like "The Coral Architects" in various resolutions such as HD 1080p or 4K Ultra HD.

### 2. Roles
The observed roles are:
- member
- premium

### 3. Flow per role
#### Member
1. Enters `/watch/:id::overlay+s002039` screen.
2. Sees "The Coral Architects" with options like "HD 1080p" and a notice about Streamly using cookies.
3. Can click "Accept" to transition to `/watch/:id::overlay+s9b8b43`, which may offer additional options like "4K Ultra HD".
4. Can click "← Back" to exit to `/browse::s2c425e`.

#### Premium
1. Enters `/watch/:id::overlay+s002039` screen.
2. Sees "The Coral Architects" with options like "HD 1080p" and a notice about Streamly using cookies.
3. Can click "Accept" to transition to `/watch/:id::overlay+s9b8b43`, which may offer additional options like "4K Ultra HD".
4. Can click "← Back" to exit to `/browse::s633472`.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The watch capability depends on the browse capability, as users can exit from watch screens to browse screens by clicking the "← Back" button.

### 7. Implicit metric
_(no evidence observed)_