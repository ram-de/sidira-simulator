### 1. User goal
Learn about Streamly and sign up for an account.

### 2. Roles
The observed roles are:
- guest
- member
- premium

### 3. Flow per role
All roles (guest, member, premium) follow the same flow:
1. Enter the landing page at `/::sfb8cd5` or `/::scdffb1`.
2. View the headings and copy, including "Unlimited stories. One small price.", "Pick the plan that fits", and options for "Member" and "Premium" plans.
3. Click the 'Get Started' button to proceed to the signup process.
4. Alternatively, click 'Sign In' to log in if they already have an account, or click 'Help' to access the help center.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The landing capability depends on the following capabilities:
- Help capability (`/help::sdfec15`, `/help::s9ca1b4`) for when the user clicks the 'Help' or 'Help Center' links.
- Login capability (`/login::login+s142a09`, `/login::login+sabcaae`) for when the user clicks the 'Sign In' link.
- Signup capability (`/signup::s2a640d`, `/signup::s8b8d39`) for when the user clicks the 'Get Started' button.

### 7. Implicit metric
_(no evidence observed)_