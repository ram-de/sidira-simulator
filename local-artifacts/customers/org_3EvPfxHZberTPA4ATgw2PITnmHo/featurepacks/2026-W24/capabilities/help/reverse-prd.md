### 1. User goal
The user goal is to find answers to common questions about Streamly, as indicated by the copy "Quick answers to common questions" on the `/help::sdfec15` and `/help::s9ca1b4` screens.

### 2. Roles
The observed roles are:
* guest
* member
* premium

All roles have access to the same help screens and transitions.

### 3. Flow per role
The flow for all roles is as follows:
1. Enter the `/help::sdfec15` screen, which displays the Help Center with headings and copy including "What do I get with Premium?" and "Can I watch without an account?"
2. Click the 'Accept' button to transition to the `/help::s9ca1b4` screen, which displays the same Help Center content.
Both guest, member, and premium roles follow this same flow.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The help capability has dependencies on the following capabilities:
* The main Streamly page (`/::sfb8cd5` and `/::scdffb1`), which can be accessed by clicking the 'STREAMLY' link on the `/help::sdfec15` and `/help::s9ca1b4` screens, respectively.
* The login capability (`/login::login+s142a09` and `/login::login+sabcaae`), which can be accessed by clicking the 'Sign In' link on the `/help::sdfec15` and `/help::s9ca1b4` screens, respectively.

### 7. Implicit metric
_(no evidence observed)_