### 1. User goal
Create a new Streamly account.

### 2. Roles
The following roles are observed:
- Guest
- Member
- Premium

### 3. Flow per role
The flow for each role is as follows:
- **Guest**: 
  1. `/signup::s2a640d` (Create your account) -> `/signup::login+sde2e7d` (Choose a password) by clicking 'Next'
  2. `/signup::login+sde2e7d` -> `/signup::s4197c3` (Pick your plan) by clicking 'Next'
  3. `/signup::login+sde2e7d` -> `/signup::login+sb09644` (Choose a password) by clicking 'Accept'
  4. `/signup::s8b8d39` -> `/signup::login+sb09644` by clicking 'Next'
  5. `/signup::login+sb09644` -> `/signup::s2cf795` (Pick your plan) by clicking 'Next'
- **Member** and **Premium**:
  1. `/signup::s2a640d` (Create your account) -> `/signup::login+sde2e7d` (Choose a password) by clicking 'Next'
  2. `/signup::s2a640d` -> `/signup::s8b8d39` by clicking 'Accept'
  3. `/signup::s8b8d39` -> `/signup::login+sb09644` by clicking 'Next'
  4. `/signup::login+sde2e7d` -> `/signup::s4197c3` by submitting the login form
  5. `/signup::login+sb09644` -> `/signup::s2cf795` by submitting the login form

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The following capabilities are referenced:
- `/help` (linked from various screens)
- `/login` (linked from various screens)
- `/profiles::chooser` (exited into from `/signup::s4197c3` and `/signup::s2cf795`)

### 7. Implicit metric
_(no evidence observed)_