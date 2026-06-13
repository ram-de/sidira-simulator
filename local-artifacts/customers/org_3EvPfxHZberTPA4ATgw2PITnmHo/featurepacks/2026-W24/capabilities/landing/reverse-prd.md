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
- From `/::sfb8cd5`, the user can click on the "Get Started" link to exit into the signup capability.
- The user can also click on the "Accept" button to transition to screen `/::scdffb1`.
- On `/::scdffb1`, the user sees similar headings and copy as on `/::sfb8cd5`.
- From both screens, the user can also click on "Sign In" to exit into the login capability or click on "Help" to exit into the help capability.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The landing capability depends on the following capabilities:
- Help capability (`/help::sdfec15`, `/help::s9ca1b4`)
- Login capability (`/login::login+s142a09`, `/login::login+sabcaae`)
- Signup capability (`/signup::s2a640d`, `/signup::s8b8d39`)

### 7. Implicit metric
_(no evidence observed)_