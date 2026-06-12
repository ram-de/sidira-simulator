### 1. User goal
Log in to an existing Streamly account.

### 2. Roles
The following roles are observed to interact with the login capability: 
- guest
- member
- premium

### 3. Flow per role
#### Guest
1. The guest starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The guest can click on the 'STREAMLY' link to exit to `/::sfb8cd5` or `/::scdffb1`.
3. The guest can click on the 'Help' link to exit to `/help::sdfec15` or `/help::s9ca1b4`.
4. The guest can click on the 'Sign up now' link to exit to `/signup::s2a640d` or `/signup::s8b8d39`.
5. If on `/login::login+s142a09`, the guest can click the 'Accept' button to transition to `/login::login+sabcaae`.

#### Member
1. The member starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The member can submit the login form to exit to `/profiles::chooser+sab6eb8` or `/profiles::chooser+s157f95`.

#### Premium
1. The premium user starts on the `/login::login+s142a09` or `/login::login+sabcaae` screen.
2. The premium user can submit the login form to exit to `/profiles::chooser+se8c8c0` or `/profiles::chooser+sdb9b57`.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The login capability has dependencies on the following capabilities:
- `/help` (exited to via 'Help' link)
- `/signup` (exited to via 'Sign up now' link)
- `/profiles` (exited to after submitting the login form)

### 7. Implicit metric
_(no evidence observed)_