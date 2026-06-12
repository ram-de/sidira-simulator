### 1. User goal
Create a new Streamly account.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
#### Guest
1. The guest starts at `/signup::s2a640d` and clicks the 'Next' button to proceed to `/signup::login+sde2e7d`.
2. At `/signup::login+sde2e7d`, the guest clicks the 'Next' button to proceed to `/signup::s4197c3`.
3. Alternatively, the guest can submit the login form at `/signup::login+sde2e7d` to proceed to `/signup::s4197c3`.
4. The guest then proceeds to `/signup::s4197c3` and can click the 'Start Watching' button to exit the signup flow.

#### Member and Premium
1. The member/premium starts at `/signup::s2a640d` and clicks the 'Accept' button to proceed to `/signup::s8b8d39`.
2. At `/signup::s8b8d39`, the member/premium clicks the 'Next' button to proceed to `/signup::login+sb09644`.
3. The member/premium then submits the login form at `/signup::login+sb09644` to proceed to `/signup::s2cf795`.
4. The member/premium can then click the 'Start Watching' button at `/signup::s2cf795` to exit the signup flow.

### 4. Success criteria
- The user successfully creates a new Streamly account.
- The user is able to proceed through the signup flow without errors.
- The user is able to click the 'Start Watching' button to exit the signup flow.

### 5. Edge cases & failure modes
- _(no evidence observed)_

### 6. Dependencies
The signup capability depends on the following capabilities:
- `/help` (linked from various signup screens)
- `/login` (linked from various signup screens)
- `/profiles` (exited into after clicking the 'Start Watching' button)

### 7. Implicit metric
- The number of successful signups (i.e., users who complete the signup flow and click the 'Start Watching' button) can be used as an implicit metric to measure the effectiveness of the signup capability.