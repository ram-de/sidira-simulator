### 1. User goal
The user goal is to find answers to common questions about Streamly, as indicated by the copy "Quick answers to common questions" on the `/help::sdfec15` and `/help::s9ca1b4` screens.

### 2. Roles
The observed roles are:
* guest
* member
* premium

All roles have access to the same screens and transitions within the help capability.

### 3. Flow per role
The flow for all roles is as follows:
1. The user lands on the `/help::sdfec15` screen, which displays the Help Center with headings and copy including "What do I get with Premium?" and "Can I watch without an account?".
2. The user can click the 'Accept' button to transition to the `/help::s9ca1b4` screen, which has the same content as the previous screen.
3. From either screen, the user can exit the help capability by clicking the 'STREAMLY' link to navigate to a different part of the application (`/::sfb8cd5` or `/::scdffb1`), or by clicking the 'Sign In' link to navigate to the login screen (`/login::login+s142a09` or `/login::login+sabcaae`).

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The help capability has dependencies on the following capabilities:
* The login capability (`/login::login+s142a09` and `/login::login+sabcaae`), which is linked from the help screens.
* Another capability (`/::sfb8cd5` and `/::scdffb1`), which is linked from the help screens via the 'STREAMLY' link.

### 7. Implicit metric
_(no evidence observed)_