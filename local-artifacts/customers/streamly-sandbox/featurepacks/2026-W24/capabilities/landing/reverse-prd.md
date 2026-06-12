### 1. User goal
Learn about Streamly and sign up for an account.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
All roles (guest, member, premium) can access the screens `/::sfb8cd5` and `/::scdffb1`. The flow is as follows:
- The user starts on screen `/::sfb8cd5`, where they can see headings such as "Unlimited stories. One small price." and "Pick the plan that fits" along with copy describing the benefits of Streamly.
- From `/::sfb8cd5`, the user can click on the "Get Started" button to proceed to the signup process, or click on "Sign In" to log in if they already have an account.
- The user can also navigate to the help center by clicking on the "Help" link.
- After clicking the "Accept" button, the user transitions to screen `/::scdffb1`, which has similar content to `/::sfb8cd5`.
- From `/::scdffb1`, the user has the same options as on `/::sfb8cd5`: to sign up, sign in, or visit the help center.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The landing capability has dependencies on the following capabilities:
- Help capability (`/help::sdfec15`, `/help::s9ca1b4`)
- Login capability (`/login::login+s142a09`, `/login::login+sabcaae`)
- Signup capability (`/signup::s2a640d`, `/signup::s8b8d39`)

### 7. Implicit metric
_(no evidence observed)_