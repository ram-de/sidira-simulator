### 1. User goal
Create a new Streamly account.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
The flow for each role is as follows:
- **guest**: 
  1. Start at `/signup::s2a640d` and click 'Next' to proceed to `/signup::login+sde2e7d`.
  2. From `/signup::login+sde2e7d`, click 'Next' to proceed to `/signup::s4197c3`.
  3. Alternatively, from `/signup::s2a640d`, click 'Accept' to proceed to `/signup::s8b8d39`, then click 'Next' to proceed to `/signup::login+sb09644`.
  4. From `/signup::login+sb09644`, click 'Next' to proceed to `/signup::s2cf795`.
- **member** and **premium**: 
  1. Start at `/signup::s2a640d` and click 'Next' to proceed to `/signup::login+sde2e7d`.
  2. From `/signup::login+sde2e7d`, submit the login form to proceed to `/signup::s4197c3`.
  3. Alternatively, from `/signup::s2a640d`, click 'Accept' to proceed to `/signup::s8b8d39`, then click 'Next' to proceed to `/signup::login+sb09644`.
  4. From `/signup::login+sb09644`, submit the login form to proceed to `/signup::s2cf795`.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The signup capability has exits into the following capabilities:
- `/login` (via clicking 'Sign In' or 'Sign in' links)
- `/help` (via clicking 'Help' links)
- `/profiles` (via clicking 'Start Watching' button after selecting a plan)
- The root capability (`/`) is also accessible via clicking the 'STREAMLY' link.

### 7. Implicit metric
_(no evidence observed)_