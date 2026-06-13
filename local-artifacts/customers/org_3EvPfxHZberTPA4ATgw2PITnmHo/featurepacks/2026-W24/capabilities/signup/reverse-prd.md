### 1. User goal
Create a new Streamly account.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
The flow for each role is as follows:
- **Guest**: 
  1. Starts at `/signup::s2a640d` and clicks 'Next' to proceed to `/signup::login+sde2e7d`.
  2. Submits the form at `/signup::login+sde2e7d` to proceed to `/signup::s4197c3`.
  3. Clicks 'Start Watching' at `/signup::s4197c3` to exit the signup flow.
- **Member** and **Premium**:
  1. Start at `/signup::s2a640d` and can click 'Next' to proceed to `/signup::login+sde2e7d` or 'Accept' to proceed to `/signup::s8b8d39`.
  2. From `/signup::login+sde2e7d`, they submit the form to proceed to `/signup::s4197c3`.
  3. Alternatively, from `/signup::s8b8d39`, they click 'Next' to proceed to `/signup::login+sb09644`, and then submit the form to proceed to `/signup::s2cf795`.
  4. Click 'Start Watching' at either `/signup::s4197c3` or `/signup::s2cf795` to exit the signup flow.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The signup capability has dependencies on the following capabilities:
- Help (`/help::sdfec15`, `/help::s9ca1b4`)
- Login (`/login::login+s142a09`, `/login::login+sabcaae`)
- Profiles (`/profiles::chooser+sab6eb8`, `/profiles::chooser+s157f95`)

### 7. Implicit metric
_(no evidence observed)_